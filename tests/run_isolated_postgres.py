"""Run reviewed test drafts on a disposable Unix-socket-only PostgreSQL instance.

Usage: .venv/bin/python tests/run_isolated_postgres.py --bin-dir /tmp/.../bin
No Docker, system install, TCP listener, application environment, or production URL.
"""
import argparse
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bin-dir', type=Path, required=True)
    args = parser.parse_args()
    binaries = args.bin_dir.resolve(strict=True)
    for name in ('initdb', 'pg_ctl', 'createdb', 'postgres'):
        if not (binaries / name).is_file():
            parser.error('Missing PostgreSQL binary: ' + name)
    root = Path(__file__).resolve().parents[1]
    work = Path(tempfile.mkdtemp(prefix='hotel-pg-test-', dir='/tmp'))
    socket = work / 'socket'
    socket.mkdir(mode=0o700)
    identity = pwd.getpwnam('nobody') if os.geteuid() == 0 else None
    if identity:
        os.chown(work, identity.pw_uid, identity.pw_gid)
        os.chown(socket, identity.pw_uid, identity.pw_gid)
    def drop_privileges():
        if identity:
            os.setgroups([])
            os.setgid(identity.pw_gid)
            os.setuid(identity.pw_uid)
    def run(name, *values):
        return subprocess.run([str(binaries / name), *values], cwd=work,
            preexec_fn=drop_privileges if identity else None, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    started = False
    try:
        run('initdb', '-D', str(work / 'data'), '--auth-local=trust', '--auth-host=reject',
            '--username=hotel_test', '--no-locale', '--encoding=UTF8')
        run('pg_ctl', '-D', str(work / 'data'), '-l', str(work / 'server.log'), '-w', 'start',
            '-o', f"-c listen_addresses='' -c unix_socket_directories={socket} -c unix_socket_permissions=0700 -p 55432")
        started = True
        run('createdb', '-h', str(socket), '-p', '55432', '-U', 'hotel_test', 'hotel_sampling_test')
        sys.path[:0] = [str(root / 'backend'), str(root / 'backend/tests')]
        # Import marks with an opt-in sentinel, then use a URL object to preserve a
        # Unix socket host without adding URL query overrides to the safety guard.
        os.environ['HOTEL_STAGING_DATABASE_URL'] = 'postgresql+psycopg://hotel_test@127.0.0.1:1/hotel_sampling_test'
        from sqlalchemy import URL
        import test_staging
        test_staging.STAGING_URL = URL.create('postgresql+psycopg', username='hotel_test',
            host=str(socket), port=55432, database='hotel_sampling_test')
        print(run('postgres', '--version').stdout.strip(), flush=True)
        print('Isolated database; Unix socket only; active migration head stays 0009.', flush=True)
        import pytest
        return pytest.main(['-q', str(root / 'backend/tests/test_sampling_postgres.py'),
                            str(root / 'backend/tests/test_staging.py')])
    except subprocess.CalledProcessError as error:
        print(error.stdout, file=sys.stderr)
        raise
    finally:
        if started:
            run('pg_ctl', '-D', str(work / 'data'), '-w', 'stop', '-m', 'fast')
        # Only this runner's newly allocated data directory is removed.
        shutil.rmtree(work)


if __name__ == '__main__':
    raise SystemExit(main())
