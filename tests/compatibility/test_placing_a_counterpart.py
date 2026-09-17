from compatibility_tool.document import Pin
from compatibility_tool.pins import place_locally
from compatibility_tool.record import ResolvedPin, Source
from compatibility_world import git


def test_a_branch_pin_resolved_to_the_working_tree_is_the_sibling_itself(world):
    sibling = world.clone("adapter")
    entry = ResolvedPin(
        Pin("mustPassWith", world.url("adapter"), "branch", "main"), world.commits["adapter"], Source.WORKING_TREE
    )
    worktrees = world.temporary / "worktrees"
    assert place_locally(world.workspace / "engine", entry, worktrees) == sibling
    assert not worktrees.exists()


def test_a_commit_pin_is_a_worktree_of_the_sibling_under_the_worktree_root(world):
    world.clone("adapter")
    commit = world.commits["adapter"]
    entry = ResolvedPin(Pin("mustPassWith", world.url("adapter"), "commit", commit), commit, Source.COMMIT)
    worktrees = world.temporary / "worktrees"
    tree = place_locally(world.workspace / "engine", entry, worktrees)
    assert tree.parent == worktrees
    assert git("rev-parse", "HEAD", cwd=tree) == commit
