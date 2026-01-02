import argparse
import os
import shutil
import subprocess
import sys

from anonflow import __version_str__, paths

def check_translations():
    mo_files, po_files = set(), set()
    for root, dirs, files in os.walk(paths.TRANSLATIONS_DIR):
        for file in files:
            if file.endswith(".mo"):
                mo_files.add(file[:-3])
            if file.endswith(".po"):
                po_files.add(file[:-3])

    return mo_files == po_files

def compile_translations():
    if not shutil.which("pybabel"):
        raise RuntimeError("Pybabel not found.")

    subprocess.run(["pybabel", "compile", "-d", paths.TRANSLATIONS_DIR], check=True)
    print("Translations compilation done.")

def main():
    os.environ["VERSION"] = __version_str__

    parser = argparse.ArgumentParser(description="Anonflow project manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("start", help="Run the application locally")

    deploy_parser = subparsers.add_parser("deploy", help="Build and manage containers via docker compose")
    deploy_parser.add_argument("docker_args", nargs=argparse.REMAINDER, help="Additional docker compose commands")

    args = parser.parse_args()

    try:
        if not check_translations():
            compile_translations()

        if args.command == "start":
            print("Running 'python -m anonflow'")
            subprocess.run([sys.executable, "-m", "anonflow"], check=True)
        elif args.command == "deploy":
            if not args.docker_args:
                print("Running 'docker compose up --build'")
                subprocess.run(["docker", "compose", "up", "--build"])
            else:
                print(f"Running 'docker compose {' '.join(args.docker_args)}'")
                subprocess.run(["docker", "compose"] + args.docker_args)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
