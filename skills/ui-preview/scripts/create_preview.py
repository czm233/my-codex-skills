#!/usr/bin/env python3
"""Assemble a standalone preview with the bundled annotation UI (stdlib only)."""
import argparse
import html
from pathlib import Path
import re


def replace_region(source, name, content, js=False):
    start, end = ((f'// {name}_START', f'// {name}_END') if js else
                  (f'<!-- {name}_START -->', f'<!-- {name}_END -->'))
    if source.count(start) != 1 or source.count(end) != 1:
        raise ValueError(f'Invalid template region: {name}')
    left, rest = source.split(start)
    _, right = rest.split(end)
    return left + start + '\n' + content + '\n' + end + right


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--content', type=Path)
    parser.add_argument('--controls', type=Path)
    parser.add_argument('--simulation', type=Path)
    parser.add_argument('--title', default='界面预演')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    template = Path(__file__).resolve().parents[1] / 'assets' / 'preview.html'
    inputs = [template] + [p for p in (args.content, args.controls, args.simulation) if p]
    if any(args.output.resolve() == p.resolve() for p in inputs):
        parser.error('Output must not overwrite an input or the installed template')
    if (args.controls or args.simulation) and not args.content:
        parser.error('--controls/--simulation require --content')
    source = template.read_text()
    if args.content:
        content = args.content.read_text()
        if re.search(r'\bid\s*=\s*[\'\"](?:product|pick|notes|bubble|sharp-cursor)[\'\"]', content):
            parser.error('Content duplicates a reserved annotation ID')
        source = replace_region(source, 'PRODUCT', content)
        source = replace_region(source, 'CONTROLS', args.controls.read_text() if args.controls else '')
        source = replace_region(source, 'DEMO_STATE', '', js=True)
        simulation = args.simulation.read_text() if args.simulation else ''
        if re.search(r'</script', simulation, re.I):
            parser.error('Simulation must be JavaScript, not HTML script tags')
        source = replace_region(source, 'SIMULATION', simulation, js=True)
    source = re.sub(r'<title>.*?</title>', lambda _: '<title>' + html.escape(args.title) + '</title>', source, count=1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(source)
    print(args.output)


if __name__ == '__main__':
    main()
