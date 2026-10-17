import copy
from pathlib import Path
import sys

import nibabel as nib
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from converter import load_source, validate_label_image,check_hemisphere


@pytest.fixture
def valid_image():
    # Construct a valid label atlas: unit tests require no redistributed data.
    values = np.ones(10242, dtype=np.int32)
    values[0] = 0
    image = nib.gifti.GiftiImage(darrays=[nib.gifti.GiftiDataArray(values, intent='NIFTI_INTENT_LABEL')])
    for key, name, rgba in [(0, 'background', (0., 0., 0., 0.)),
                            (1, 'synthetic_region', (0.2, 0.4, 0.6, 1.))]:
        label = nib.gifti.GiftiLabel(key=key, red=rgba[0], green=rgba[1], blue=rgba[2], alpha=rgba[3])
        label.label = name
        image.labeltable.labels.append(label)
    validate_label_image(image)
    return image


def test_atlas_without_dictionary_is_rejected(valid_image):
    valid_image.labeltable=nib.gifti.GiftiLabelTable()
    with pytest.raises(ValueError,match='Missing original label dictionary'):
        validate_label_image(valid_image)


def test_wrong_density_is_rejected(valid_image):
    valid_image.darrays[0].data=valid_image.darrays[0].data[:100]
    with pytest.raises(ValueError,match='10242 vertices'):
        validate_label_image(valid_image)


def test_continuous_metric_is_not_mistaken_for_atlas(valid_image):
    valid_image.darrays[0].intent=nib.nifti1.intent_codes['NIFTI_INTENT_SHAPE']
    with pytest.raises(ValueError,match='LABEL intent'):
        validate_label_image(valid_image)


def test_undefined_region_id_is_rejected(valid_image):
    valid_image.darrays[0].data[100]=100000
    with pytest.raises(ValueError,match='Missing original label dictionary'):
        validate_label_image(valid_image)


def test_colour_metadata_is_required(valid_image):
    valid_image.labeltable.labels[1].red=None
    with pytest.raises(ValueError,match='RGBA'):
        validate_label_image(valid_image)


def test_duplicate_dictionary_ids_are_rejected(valid_image):
    valid_image.labeltable.labels.append(copy.deepcopy(valid_image.labeltable.labels[1]))
    with pytest.raises(ValueError,match='Duplicate'):
        validate_label_image(valid_image)


@pytest.mark.parametrize('filename,hemi',[('lh.atlas.annot','R'),('rh.atlas.annot','L'),
                                        ('atlas_hemi-L_dseg.label.gii','R')])
def test_filename_hemisphere_mismatch_is_rejected(filename,hemi):
    with pytest.raises(ValueError,match='Hemisphere mismatch'):
        check_hemisphere(filename,hemi)
