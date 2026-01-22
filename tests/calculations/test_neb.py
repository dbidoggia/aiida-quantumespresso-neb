"""Tests for the `NebCalculation` class"""


from aiida import orm
from aiida.common import datastructures
from aiida.common.exceptions import InputValidationError
from aiida.common.warnings import AiidaDeprecationWarning
import pytest

@pytest.fixture
def generate_inputs_neb(fixture_code, generate_structure, generate_upf_data, generate_kpoints_mesh):
    """Generate inputs for a `NebCalculation`."""
    
    def _generate_inputs_neb(num_of_images=3,images=None):

        first_structure = generate_structure()
        last_structure = generate_structure()
        inputs = {
            'parameters': orm.Dict(dict={
                    'PATH': {
                        'num_of_images': num_of_images,
                    }
                }),
            'code': fixture_code('quantumespresso.neb'),
            'pw' : {
                    'parameters':  orm.Dict({
                        'CONTROL': {
                            'calculation': 'scf'
                        },
                        'SYSTEM': {
                            'ecutrho': 240.0,
                            'ecutwfc': 30.0
                        },
                        'ELECTRONS': {
                            'electron_maxstep': 60,
                        }
                    }),
                    'kpoints': generate_kpoints_mesh(2),
                    'pseudos': {kind: generate_upf_data(kind) for kind in first_structure.get_kind_names()},
            }
        }
        if images is None:
            inputs.update({
                'first_structure': first_structure,
                'last_structure': last_structure,
            })
        elif isinstance(images, list):
            inputs.update({
                'images': images,
            })
        elif isinstance(images, int):
            image_list = []
            for _ in range(images):
                image_list.append(generate_structure())
            inputs.update({
                'images': orm.TrajectoryData(image_list),
            })
        else:  
            raise InputValidationError('images should be either None, an integer or a list of structures.')

        return inputs
    return _generate_inputs_neb

@pytest.mark.parametrize('num_of_images', [3, 5])
@pytest.mark.parametrize('images', [True, False])
def test_neb_default(fixture_sandbox, generate_calc_job, generate_inputs_neb, file_regression, num_of_images, images):
    """Test a default NEB calculation with first and last structures."""
    entry_point_name = 'quantumespresso.neb'
    inputs = generate_inputs_neb(num_of_images=num_of_images, images=num_of_images if images else None)
    calc_info = generate_calc_job(fixture_sandbox, entry_point_name, inputs)

    assert 'aiida.out' in calc_info.retrieve_list
    with fixture_sandbox.open('neb.dat') as handle:
        input_written = handle.read()
    file_regression.check(input_written, encoding='utf-8', extension='.dat')
    if images:
        assert sorted(fixture_sandbox.get_content_list()) == sorted(['neb.dat', 'out', 'pseudo',] + [f'pw_{i+1}.in' for i in range(num_of_images)])
    else:
        assert sorted(fixture_sandbox.get_content_list()) == sorted(['neb.dat', 'out', 'pseudo', 'pw_1.in', 'pw_2.in'])
    for i in range(num_of_images if images else 2):
        with fixture_sandbox.open(f'pw_{i+1}.in') as handle:
            pw1_input_written = handle.read()
        file_regression.check(pw1_input_written, encoding='utf-8', extension=f'.pw{i+1}.in')