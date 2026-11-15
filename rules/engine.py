"""P4: Pennsylvania-wide sorting decisions with fail-closed local verification.

Statewide PA DEP advisories are *information*, not blanket permission to put an
item in a particular curbside bin. Only a specific, verified collection-program
profile can return a real RECYCLE/COMPOST/LANDFILL destination.

The public return contract is exactly {bin, message, rule_id, source_url}.
Python 3.11+, standard library only.
"""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

ALLOWED_BINS = {'RECYCLE', 'COMPOST', 'LANDFILL', 'UNKNOWN'}
PA_STATEWIDE = 'PA_STATEWIDE'
DEFAULT_LOCATION = PA_STATEWIDE
ROOT = Path(__file__).resolve().parent
PA_POLICIES = ROOT / 'locations' / 'PA_STATEWIDE.json'
DEMO_POLICIES = ROOT / 'demo_rules.json'


def _unknown(message: str, *, rule_id: str | None = None,
             source_url: str | None = None) -> dict[str, Any]:
    return {'bin': 'UNKNOWN', 'message': message, 'rule_id': rule_id,
            'source_url': source_url}


def _norm(text: str) -> str:
    return ' '.join(text.casefold().strip().split())


def _source_valid(obj: Mapping[str, Any], prefix: str = '') -> bool:
    url = obj.get(prefix + 'source_url')
    checked = obj.get(prefix + 'verified_on')
    if not isinstance(url, str):
        return False
    u = urlparse(url)
    if u.scheme != 'https' or not u.netloc or not isinstance(checked, str):
        return False
    try:
        d = date.fromisoformat(checked)
    except ValueError:
        return False
    return d <= date.today()


def _load(path: Path) -> dict[str, Any] | None:
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        return None
    return obj if isinstance(obj, dict) else None


def _matches(obj: Mapping[str, Any], item_key: str) -> bool:
    main = obj.get('item', '')
    aliases = obj.get('aliases', [])
    if not isinstance(main, str) or not isinstance(aliases, list) or not all(isinstance(x, str) for x in aliases):
        return False
    return item_key in {_norm(n) for n in [main, *aliases]}


def _state_advisory(item_key: str) -> tuple[dict[str, Any], bool]:
    """Return grounded PA advice, and whether item is barred from ordinary bin choice."""
    obj = _load(PA_POLICIES)
    if not obj or obj.get('location_id') != PA_STATEWIDE:
        return _unknown('Pennsylvania guidance could not be loaded; verify the local collection program.'), True
    rows = obj.get('advisories')
    if not isinstance(rows, list):
        return _unknown('Pennsylvania guidance is malformed; verify the local collection program.'), True
    matches = [r for r in rows if isinstance(r, dict) and _matches(r, item_key)]
    if len(matches) > 1:
        return _unknown('Conflicting Pennsylvania guidance; please check the official DEP advice.'), True
    if matches:
        r = matches[0]
        if r.get('status') == 'verified' and _source_valid(r) and isinstance(r.get('message'), str) and r.get('rule_id'):
            return _unknown(r['message'], rule_id=r['rule_id'], source_url=r['source_url']), r.get('special_collection') is True
        return _unknown('The source for this item could not be verified; check Pennsylvania DEP.'), True
    return _unknown('Pennsylvania-wide guidance does not establish a bin for this item. Check your municipality or waste hauler before disposal.'), False


def decide(recognition: Mapping[str, Any], location: str = DEFAULT_LOCATION,
           attributes: Mapping[str, Any] | None = None,
           rules_path: str | Path | None = None, *,
           demo_mode: bool = False,
           program_id: str | None = None) -> dict[str, Any]:
    """Choose a bin only for a verified local collection program or overt demo.

    recognition: P2 output with item/material/needs_clarification/question.
    attributes: confirmed human/station facts, e.g. {'empty': True}.
    program_id: selected and verified Pennsylvania municipal/hauler program.
    rules_path: the corresponding verified program JSON path.
    No source verification is performed over the network; a human must inspect
    source content before setting status='verified'.
    """
    if location not in (PA_STATEWIDE, 'DEMO_ONLY'):
        return _unknown('Set the project region to Pennsylvania; this engine does not cover other states.')
    if not isinstance(recognition, Mapping):
        return _unknown('The camera did not return a usable recognition result.')
    if recognition.get('needs_clarification') is not False:
        return _unknown(str(recognition.get('question') or 'Please inspect the item or packaging.'))
    item = recognition.get('item')
    if not isinstance(item, str) or not item.strip():
        return _unknown('The object could not be identified. Check it manually.')
    attrs = attributes if isinstance(attributes, Mapping) else {}
    key = _norm(item)

    if demo_mode:
        if location != 'DEMO_ONLY' or rules_path is not None or program_id is not None:
            return _unknown('Demo data can only be used in explicitly labeled DEMO_ONLY mode.')
        data = _load(DEMO_POLICIES)
        if not data or data.get('demo_only') is not True or data.get('location_id') != 'DEMO_ONLY':
            return _unknown('Demo rule file is missing or not labeled as demo data.')
        candidates = [r for r in data.get('rules', []) if isinstance(r, dict) and _matches(r, key)]
        if len(candidates) != 1:
            return _unknown('No matching demo rule; try a labeled practice object.')
        row = candidates[0]
        if row.get('status') != 'demo' or row.get('demo_only') is not True:
            return _unknown('The matching rule is not marked DEMO ONLY.')
        if row.get('bin') not in ALLOWED_BINS - {'UNKNOWN'}:
            return _unknown('Demo rule has an invalid bin.')
        return _evaluate_conditions(row, attrs, 'DEMO ONLY — NOT VERIFIED: ', None)

    if location == 'DEMO_ONLY':
        return _unknown('Demo rules are disabled. Select Pennsylvania for real policy guidance.')

    advisory, blocked = _state_advisory(key)
    if blocked:
        return advisory

    # Statewide guidance alone cannot decide a curbside destination. Require
    # *both* an explicitly selected program and its independently verified file.
    if not program_id or rules_path is None:
        return advisory
    data = _load(Path(rules_path))
    if not data or data.get('location_id') != PA_STATEWIDE or data.get('demo_only') is not False:
        return _unknown('The local program file is missing, invalid, or marked as demo data.')
    if (data.get('program_id') != program_id or data.get('program_verified') is not True
            or not _source_valid(data, 'program_')):
        return _unknown('This collection program and its official source have not been verified.')
    streams = data.get('available_bins')
    if not isinstance(streams, list) or not all(b in ALLOWED_BINS - {'UNKNOWN'} for b in streams):
        return _unknown('The station’s available collection streams are not verified.')
    rows = data.get('rules')
    if not isinstance(rows, list):
        return _unknown('The local disposal rules are malformed.')
    matches = [r for r in rows if isinstance(r, dict) and _matches(r, key)]
    if len(matches) != 1:
        return advisory
    row = matches[0]
    if row.get('status') != 'verified' or not row.get('rule_id') or not _source_valid(row):
        return _unknown('This specific item lacks a source-verified collection rule.')
    if row.get('bin') not in ALLOWED_BINS - {'UNKNOWN'}:
        return _unknown('This rule does not specify a supported disposal stream.')
    if row['bin'] not in streams:
        return _unknown('The required collection bin is not confirmed at this station.')
    # Compost rules require stronger verification: a specifically supported and
    # currently accessible food/yard waste stream; a green logo isn't enough.
    if row['bin'] == 'COMPOST' and data.get('compost_stream_confirmed') is not True:
        return _unknown('No compost stream is confirmed for this collection program.')
    return _evaluate_conditions(row, attrs, '', row['source_url'])


def _evaluate_conditions(row: Mapping[str, Any], attrs: Mapping[str, Any],
                         prefix: str, source_url: str | None) -> dict[str, Any]:
    requires = row.get('requires', {})
    if not isinstance(requires, dict) or any(type(v) is not bool for v in requires.values()):
        return _unknown('The disposal rule has invalid item conditions.')
    for field, expected in requires.items():
        if field not in attrs or type(attrs[field]) is not bool:
            return _unknown(str(row.get('question_when_missing') or f'Please confirm: {field.replace("_", " ")}.'),
                            source_url=source_url)
        if attrs[field] != expected:
            return _unknown('This item does not satisfy the rule conditions; check local instructions.', source_url=source_url)
    message = row.get('message')
    if not isinstance(message, str) or not message.strip():
        return _unknown('A verified rule explanation is required.')
    return {'bin': row['bin'], 'message': prefix + message,
            'rule_id': row.get('rule_id'), 'source_url': source_url}
