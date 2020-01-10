
from user_sync.post_sync.connectors.sign_sync import SignConnector



def test_common_groups():

    group = SignConnector.common_group(['A', 'B', 'C'], ['D', 'E', 'F', 'B'], "default")
    assert group == "B"

    group = SignConnector.common_group(['A', 'B', 'C'], ['D', 'E', 'F'], "default")
    assert group == "default"

