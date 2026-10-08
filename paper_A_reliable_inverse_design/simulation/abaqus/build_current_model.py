"""Historical x/Standard generator using script_first_config_20260924.json.

This does not implement the current M09 baseline. Never submit jobs.

Usage: python build_current_model.py mesh.inp new_output_directory job_name
Run the generated script through Abaqus CAE noGUI separately to write the INP.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re


def generate(mesh, output, job):
    here = Path(__file__).resolve().parent
    root = here.parent.parent
    config_path = here / 'script_first_config_20260924.json'
    config = json.loads(config_path.read_text(encoding='utf-8'))
    source = Path(config['source_script'])
    if hashlib.sha256(source.read_bytes()).hexdigest() != config['source_sha256']:
        raise ValueError('Author script changed: re-audit source before generating')
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', job):
        raise ValueError('Use an ASCII job name beginning with a letter')
    mesh = Path(mesh).resolve(strict=True)
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError('Choose a new output directory; existing cases are immutable')
    # This adapter is for the script-first x/Standard baseline only.
    if (config['loading']['axis'], config['step']['procedure'],
            config['material']['type'], config['boundary']['type']) != (
            'x', 'StaticStep', 'POLYNOMIAL', 'six_face_displacement_not_strict_PBC'):
        raise ValueError('Unsupported physical configuration; do not silently reuse this adapter')
    template = root / 'audits/m05_small_mechanism_pilot_20260919/scripts/gen_build_model.py'
    spec = importlib.util.spec_from_file_location('small_existing_generator', template)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    script = module.make_script(str(mesh), job)

    def replace_once(old, new):
        nonlocal script
        if script.count(old) != 1:
            raise ValueError('Template drift: ' + old)
        script = script.replace(old, new)

    step = config['step']
    replace_once('maxNumInc=1000,\n             initialInc=0.01, minInc=0.001, nlgeom=ON)',
                 f"maxNumInc={step['maxNumInc']},\n             initialInc={step['initialInc']}, "
                 f"minInc={step['minInc']}, timePeriod={step['timePeriod']}, "
                 f"maxInc={step['maxInc']}, nlgeom=ON)")
    replace_once('u1=-10.0, u2=UNSET, u3=UNSET)',
                 f"u1={config['loading']['drive_u1_mm']}, u2=UNSET, u3=UNSET)")
    replace_once('numIntervals=40)', f"numIntervals={config['outputs']['field_numIntervals']})")
    if config['outputs']['history_numIntervals'] != 20:
        raise ValueError('This adapter requires script history intervals=20')
    replace_once('numCpus=8, numDomains=8',
                 f"numCpus={config['resources']['numCpus']}, numDomains={config['resources']['numDomains']}")
    ast.parse(script)
    if '.submit(' in script:
        raise ValueError('Generated build must never submit')
    output.mkdir(parents=True)
    (output / 'build_model.py').write_text(script, encoding='utf-8')
    (output / 'config_snapshot.json').write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding='utf-8')
    provenance = {'mesh_path': str(mesh), 'mesh_sha256': hashlib.sha256(mesh.read_bytes()).hexdigest(),
                  'template_sha256': hashlib.sha256(template.read_bytes()).hexdigest(),
                  'config_sha256': hashlib.sha256(config_path.read_bytes()).hexdigest(),
                  'build_script_sha256': hashlib.sha256((output / 'build_model.py').read_bytes()).hexdigest(),
                  'status': 'build_script_generated_only_not_solved'}
    (output / 'build_provenance.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
    print(output / 'build_model.py')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mesh')
    parser.add_argument('output')
    parser.add_argument('job')
    args = parser.parse_args()
    generate(args.mesh, args.output, args.job)
