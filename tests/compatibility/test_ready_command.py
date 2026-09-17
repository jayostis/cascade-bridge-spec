def test_ready_fails_a_pin_to_a_feature_branch(world):
    said = world.tool(world.engine(world.adapter_pin(branch="feat/next")), ("ready", 1))
    assert "branch feat/next: not the default branch, main" in said


def test_ready_fails_a_commit_not_on_the_default_branch(world):
    feature = world.commits["adapter feat/next"]
    said = world.tool(world.engine(world.adapter_pin(commit=feature)), ("ready", 1))
    assert f"{feature} is not on main, the default branch" in said


def test_ready_passes_a_tag_on_the_default_branch_and_the_spec_pin(world):
    said = world.tool(world.engine(world.adapter_pin(tag="v1")), ("ready", 0))
    adapter, specification = world.commits["adapter"], world.commits["specification"]
    assert f"mustPassWith: {world.url('adapter')} tag v1: {adapter} is on main" in said
    assert f"specPin: {world.url('specification')} commit {specification}: {specification} is on main" in said


def test_ready_passes_a_pin_to_the_default_branch(world):
    said = world.tool(world.engine(world.adapter_pin(branch="main")), ("ready", 0))
    assert "branch main: the default branch" in said
