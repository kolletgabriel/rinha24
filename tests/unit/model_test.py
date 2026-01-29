from rinha24.models import Transaction

from pydantic import ValidationError
from pytest import raises
from hypothesis import given, strategies as st


@given(st.fixed_dictionaries({}, optional={
    'value': st.integers(None, 0) | st.floats(),
    'type': st.characters(exclude_characters=('c', 'd')) | st.just(''),
    'desc': st.text(min_size=11) | st.just('')

}))
def test_bad_jsons(j):
    with raises(ValidationError):
        Transaction(**j)


@given(st.fixed_dictionaries({
    'value': st.integers(1, None),
    'type': st.just('c') | st.just('d'),
    'desc': st.text(min_size=1, max_size=10)
}))
def test_good_jsons(j):
    new_transaction = Transaction(**j)
    assert new_transaction.value == j['value']
    assert new_transaction.type == j['type']
    assert new_transaction.desc == j['desc']
