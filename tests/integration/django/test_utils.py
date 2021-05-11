import pytest

from odata_query.django import utils

from .models import Author, BlogPost


@pytest.mark.parametrize(
    "root_model, rel, exp_model, exp_rel",
    [
        (Author, "blogposts", BlogPost, "authors"),
        (BlogPost, "comments__author", Author, "comments__blogpost"),
    ],
)
def test_reverse_relationship(root_model, rel, exp_model, exp_rel):
    res_rel, res_model = utils.reverse_relationship(rel, root_model)

    assert res_rel == exp_rel
    assert res_model is exp_model
