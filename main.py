import sys


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--cli" in argv or "--nogui" in argv:
        import link

        link.Link().run()
        return 0

    import gui

    return int(gui.main())


if __name__ == "__main__":
    raise SystemExit(main())
