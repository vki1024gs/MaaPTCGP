"""Build the optional MaaPiCli runtime independently of desktop packaging."""

from ci import install


if __name__ == "__main__":
    install.require_supported_target()
    executable = install.working_dir / "deps" / "bin" / install.maa_pi_cli_name()
    if not executable.is_file():
        raise SystemExit(
            f"Missing optional CLI executable: {executable}\n"
            "Prepare MaaPiCli and its matching MaaFramework runtime in deps/bin first. "
            "MaaFramework v5.15.0+ packages do not bundle MaaPiCli."
        )

    install.clean_install_cli()
    install.install_maafw_for_cli()
    install.install_cli_resource()
    install.verify_cli_install()
    print(f"Install MaaPiCli runtime to {install.install_cli_path} successfully.")
