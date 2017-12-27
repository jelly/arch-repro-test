#!/usr/bin/env python

import tarfile
import os
import subprocess
import sys
import shutil

from datetime import datetime



SERVER_FORMAT = 'Server = https://archive.archlinux.org/repos/{}/{}/{}/$repo/os/$arch\n'

def parse_installed(data):
    data = data.decode('utf-8')
    packages = []
    for line in data.split('\n'):
        if line.startswith('installed'):
            pkg = line.split(' = ')[1]
            packages.append(pkg)
    return packages


def extract_builddate(data):
    for line in data.split(b'\n'):
        if line.startswith(b'builddate'):
            return line.split(b' = ')[1]

def main(filename):
    tar = tarfile.open(filename)
    for member in tar.getmembers():
        if member.name == '.BUILDINFO':
            entry = tar.extractfile(member)
            buildinfo = entry.read()
        if member.name == '.PKGINFO':
            entry = tar.extractfile(member)
            builddate_str = extract_builddate(entry.read())

    builddate = datetime.fromtimestamp(int(builddate_str))
    if not builddate:
        print('No builddate, cannot reproduce')

    print("builddate: {}".format(builddate))
    print("month: {}, day: {}".format(builddate.month, builddate.day))

    with open('mirrorlist', 'w') as mirrorlist:
        mirrorlist.write(SERVER_FORMAT.format(builddate.year, builddate.month, builddate.day))

    if not buildinfo:
        print('No .BUILDINFO found in {}'.format(filename))

    # Parse buldinfo
    packages = parse_installed(buildinfo)
    #print(packages)
    # Handle stripping pkgver-pkgrel
    pkgnames = ['-'.join(pkg.split('-')[:-2]) for pkg in packages]
    install = ' '.join(pkgnames)

    # pyalpm?!!!
    # Pacstrap
    if os.path.exists('repro'):
        os.system('sudo rm -rf repro')
    os.makedirs('repro')
    os.system('sudo pacstrap -M -d  -C pacman.conf -c repro {}'.format(install))

    print('Verify if all packages are installed')

    # Verify installed version matches
    p = subprocess.Popen('pacman -r repro -Q', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines = p.stdout.readlines()
    if len(lines) != len(packages):
        print('Missing or too many installed packages installed in chroot')
    for line in lines:
        line = line.strip()
        line = line.decode('utf-8')
        # Replace space with - to match the BUILDINFO format
        line = line.replace(' ', '-')
        if line not in packages:
            for pkg in packages:
                pkgname = pkg.split('-')[:-2]
                if line.startswith(pkgname):
                    break
            print('Wrong installed package: {}, required: {}'.format(line, pkgname))
    retval = p.wait()


    # ASP x86_64

    # Build!


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('missing argument file.tar.xz')
        sys.exit(1)

    main(sys.argv[1])
