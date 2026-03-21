import sys
from pathlib import Path
from shutil import copyfile


def _app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _ensure_default_config() -> None:
    base_dir = _app_base_dir()
    env_path = base_dir / "settings.env"
    if env_path.exists():
        return
    example_path = base_dir / "settings.env.example"
    if not example_path.exists():
        return
    try:
        copyfile(example_path, env_path)
    except Exception:
        return


def main(argv: list[str] | None = None) -> int:
    _ensure_default_config()
    argv = sys.argv[1:] if argv is None else argv
    if "--cli" in argv or "--nogui" in argv:
        import link

        link.Link().run()
        return 0

    import gui

    return int(gui.main())


if __name__ == "__main__":
    raise SystemExit(main())
