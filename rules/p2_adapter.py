"""P4 adapter for P2's documented CLIP and OWLv2 recognition outputs.

Never let recognition alone override a verified local-program requirement.
Call process_recognition() at the P3 FastAPI integration boundary rather than
passing raw P2 data directly to rules.engine.decide().

This module accepts a *single recognition dict* or a *multi recognition dict*.
It performs fail-closed uncertainty checks and enriches the existing P4 core
result without changing the core {bin,message,rule_id,source_url} contract.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from rules.engine import (
    PA_POLICIES, _load, _norm, _source_valid, decide,
)

SUPPORTED_MATERIALS = frozenset({
    'plastic', 'paper', 'cardboard', 'metal', 'glass', 'organic',
})
BLOCKED_FUSION_STATES = frozenset({'model_disagreement', 'unverified'})
# These are examples P2 may explicitly annotate. We DO NOT parse free-text questions
# to decide what was confirmed; conditions must be structured, human-confirmed booleans.
ALLOWED_CONDITIONS = frozenset({'empty', 'clean', 'food_soiled', 'dry', 'packaging_confirmed'})


def _get_verification_date(rule_id: str | None, source_url: str | None,
                           rules_path: str | Path | None = None) -> str | None:
    """Retrieve date from the exact record that justified this source-backed result.

    Returns None for unknown or non-source-backed results. The date is metadata,
    not independent online verification of the source's content.
    """
    if not rule_id or not source_url:
        return None
    paths = [PA_POLICIES]
    if rules_path is not None:
        paths.append(Path(rules_path))
    for path in paths:
        data = _load(path)
        if not data:
            continue
        for collection in ('advisories', 'rules'):
            rows = data.get(collection, [])
            if not isinstance(rows, list):
                continue
            for row in rows:
                if (isinstance(row, dict) and row.get('rule_id') == rule_id
                        and row.get('source_url') == source_url
                        and row.get('status') == 'verified' and _source_valid(row)):
                    return row.get('verified_on')
    return None


def _format_result(obj: Mapping[str, Any], core: Mapping[str, Any],
                   *, rules_path: str | Path | None = None,
                   question: str | None = None) -> dict[str, Any]:
    b = core['bin']
    message = str(core['message'])
    if b == 'UNKNOWN' and question is None:
        # Advisory UNKNOWN may be a collection-program question rather than a
        # visual-recognition problem; retaining the explanation is important.
        question = message
    return {
        'object_id': obj.get('object_id'),
        'item': obj.get('item') if isinstance(obj.get('item'), str) else None,
        'material': obj.get('material') if isinstance(obj.get('material'), str) else 'unknown',
        'bin': b,
        'needs_clarification': b == 'UNKNOWN',
        'message': message,
        'explanation': message,      # P2's proposed frontend alias
        'question': question if b == 'UNKNOWN' else None,
        'rule_id': core.get('rule_id'),
        'source_url': core.get('source_url'),
        'rule_checked_date': _get_verification_date(
            core.get('rule_id'), core.get('source_url'), rules_path),
    }


def _blocked(obj: Mapping[str, Any], message: str, *,
             question: str | None = None) -> dict[str, Any]:
    return _format_result(obj, {
        'bin': 'UNKNOWN', 'message': message, 'rule_id': None, 'source_url': None,
    }, question=question)


def _process_one(obj: Mapping[str, Any], *,
                 location: str, attributes: Mapping[str, Any] | None,
                 program_id: str | None, rules_path: str | Path | None,
                 demo_mode: bool, is_multi: bool) -> dict[str, Any]:
    if not isinstance(obj, Mapping):
        return _blocked({}, 'Recognition returned a malformed object. Please rescan.')

    item = obj.get('item')
    material = obj.get('material')
    if not isinstance(item, str) or not item.strip():
        return _blocked(obj, 'The AI could not identify the item. Please reposition or identify it.')
    if not isinstance(material, str) or _norm(material) not in SUPPORTED_MATERIALS:
        return _blocked(obj, 'The material is unknown or unsupported.',
                        question='Please confirm the material or use the appropriate special collection.')

    # P2 may explicitly report agreement between equivalent item descriptions,
    # e.g. "sheet of paper" (detector) and "office paper" (classifier).
    # An explicit negative or malformed value must never bypass this safety gate.
    # Older payloads without item_agreement are handled below in multi-object mode.
    if 'item_agreement' in obj:
        if type(obj['item_agreement']) is not bool:
            return _blocked(obj, 'The item-agreement flag is invalid.',
                            question='Please confirm the item.')
        if obj['item_agreement'] is False:
            return _blocked(obj, 'The detector and classifier disagree about the item.',
                            question=str(obj.get('question') or 'Please identify this item.'))
    if obj.get('prediction_agreement') is False:
        return _blocked(obj, 'The item and material predictions disagree.',
                        question='Please confirm the item and its material.')
    if obj.get('material_agreement') is False:
        return _blocked(obj, 'The detector and classifier disagree about the material.',
                        question='Please confirm the material.')
    fusion = obj.get('fusion_status')
    if fusion in BLOCKED_FUSION_STATES:
        return _blocked(obj, 'The model-fusion result is uncertain.',
                        question=str(obj.get('question') or 'Please confirm the item and material.'))
    if is_multi:
        if fusion != 'material_agreement':
            return _blocked(obj, 'The multi-object recognition agreement is not verified.')
        # New P2 payloads use the explicit boolean item_agreement checked
        # above. Legacy payloads must still match exact normalized strings;
        # never infer agreement from material agreement alone.
        if 'item_agreement' not in obj:
            detector_label = obj.get('detector_label')
            if (not isinstance(detector_label, str)
                    or _norm(detector_label) != _norm(item)):
                return _blocked(obj, 'The detector and classifier disagree about the item.',
                                question=str(obj.get('question') or 'Please identify this item.'))

    # Conditions that can be answered by a user are different from uncertain
    # identity/material. Require P2's structured clarification_type and explicit
    # boolean attributes; never infer confirmation just from wording of a question.
    if obj.get('needs_clarification') is not False:
        if obj.get('clarification_type') != 'condition':
            return _blocked(obj, str(obj.get('question') or 'Please confirm the item.'),
                            question=str(obj.get('question') or 'Please confirm the item.'))
        required = obj.get('required_attributes')
        if (not isinstance(required, list) or not required
                or any(not isinstance(k, str) or k not in ALLOWED_CONDITIONS for k in required)
                or not isinstance(attributes, Mapping)
                or any(type(attributes.get(k)) is not bool for k in required)):
            return _blocked(obj, str(obj.get('question') or 'Please confirm the item condition.'),
                            question=str(obj.get('question') or 'Please confirm the item condition.'))

    safe_input = dict(obj)
    safe_input['item'] = item.strip()
    safe_input['material'] = _norm(material)
    safe_input['needs_clarification'] = False
    core = decide(safe_input, location=location, attributes=attributes,
                  program_id=program_id, rules_path=rules_path,
                  demo_mode=demo_mode)
    return _format_result(obj, core, rules_path=rules_path)


def process_recognition(recognition: Mapping[str, Any], *,
                        location: str = 'PA_STATEWIDE',
                        attributes: Mapping[str, Any] | None = None,
                        attributes_by_object: Mapping[int, Mapping[str, Any]] | None = None,
                        program_id: str | None = None,
                        rules_path: str | Path | None = None,
                        demo_mode: bool = False) -> dict[str, Any]:
    """Adapt P2's single-/multi-object results to P3-ready decisions.

    Single object: top-level `bin` is safe for direct hardware dispatch.
    Multiple objects: top-level `bin` is ALWAYS UNKNOWN. P3 must show each
    decision, let the user select an object, then dispatch that object's bin.
    `object_id` is valid only for the current capture, never across images.
    """
    if not isinstance(recognition, Mapping):
        recognition = {}
    is_multi = 'objects' in recognition
    if is_multi:
        raw = recognition.get('objects')
        if not isinstance(raw, list) or not all(isinstance(x, Mapping) for x in raw):
            return {'bin': 'UNKNOWN', 'message': 'Malformed detection results. Rescan.',
                    'object_count': 0, 'multiple_items': False,
                    'objects': [], 'needs_clarification': True}
        count = recognition.get('object_count')
        if type(count) is not int or count != len(raw):
            return {'bin': 'UNKNOWN', 'message': 'Detection count mismatch. Rescan.',
                    'object_count': len(raw), 'multiple_items': len(raw) > 1,
                    'objects': [], 'needs_clarification': True}
        ids = [x.get('object_id') for x in raw]
        if any(type(i) is not int or i < 1 for i in ids) or len(set(ids)) != len(ids):
            return {'bin': 'UNKNOWN', 'message': 'Invalid object identifiers. Rescan.',
                    'object_count': len(raw), 'multiple_items': len(raw) > 1,
                    'objects': [], 'needs_clarification': True}
        raw_objects = raw
    else:
        raw_objects = [recognition]

    if not raw_objects:
        return {'bin': 'UNKNOWN', 'message': 'No waste item was detected. Reposition the item.',
                'object_count': 0, 'multiple_items': False,
                'objects': [], 'needs_clarification': True}

    choices = []
    for obj in raw_objects:
        obj_attrs = (attributes_by_object.get(obj['object_id'])
                     if (is_multi and isinstance(attributes_by_object, Mapping))
                     else attributes if not is_multi else None)
        choices.append(_process_one(obj, location=location,
                                    attributes=obj_attrs, program_id=program_id,
                                    rules_path=rules_path, demo_mode=demo_mode,
                                    is_multi=is_multi))

    n = len(choices)
    if n > 1:
        top = {'bin': 'UNKNOWN',
               'message': 'Multiple items detected. Select one object to show its bin.',
               'needs_clarification': True}
    else:
        top = {'bin': choices[0]['bin'], 'message': choices[0]['message'],
               'needs_clarification': choices[0]['needs_clarification']}
    return {**top, 'object_count': n, 'multiple_items': n > 1,
            'objects': choices}
