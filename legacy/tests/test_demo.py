import pytest

import run_demo


def test_auto_approval_cannot_be_used_with_ollama(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["run_demo.py", "--yes", "--model", "llama3.1"])
    with pytest.raises(SystemExit) as error:
        run_demo.main()
    assert error.value.code == 2
    assert "only allowed with the scripted model" in capsys.readouterr().err


@pytest.mark.parametrize("action,args", [
    ("update_tracker", {"offer_id": "o1", "status": "interested", "match_score": 90}),
    ("submit_application", {"offer_id": "o1", "letter": "A full application letter."}),
])
def test_human_checkpoint_shows_action_and_all_arguments(monkeypatch, capsys, action, args):
    monkeypatch.setattr("builtins.input", lambda prompt: "yes")
    assert run_demo.human_approve(action, args) is True
    output = capsys.readouterr().out
    assert action in output
    for key, value in args.items():
        assert key in output and str(value) in output


def test_human_checkpoint_defaults_to_denial(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    assert run_demo.human_approve("update_tracker", {"offer_id": "o1"}) is False


@pytest.mark.parametrize("auto_approve", [False, True])
def test_scripted_demo_runs_with_interactive_and_automatic_approval(
        monkeypatch, tmp_path, capsys, auto_approve):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "cv.txt").write_text("Python CV", encoding="utf-8")
    monkeypatch.setattr(run_demo, "ROOT", tmp_path)
    monkeypatch.setattr("sys.argv", ["run_demo.py"] + (["--yes"] if auto_approve else []))
    prompts = []

    def approve(prompt):
        prompts.append(prompt)
        return "yes"

    monkeypatch.setattr("builtins.input", approve)
    run_demo.main()
    output = capsys.readouterr().out
    assert "Stop reason: done" in output and "sent: ['o1']" in output
    assert len(prompts) == (0 if auto_approve else 2)
    assert (tmp_path / "logs" / "run.jsonl").exists()
