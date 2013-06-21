import os
import gzip, tarfile, datetime, re, shutil
from zipfile import ZipFile, BadZipfile

def zdsplode(name, verbose=False):
    start_dir = os.path.abspath(os.getcwd())

    # Match on the filename
    # [base].[ext]
    # where ext is one of zip, tar, gz, tgz, tar.gz, or tar.bz2
    m = re.match(r'^(?P<base>.*?)[.](?P<ext>zip|tar|tgz|tar\.gz|tar\.bz2|tar\.bz|gz)$', name)
    if not m:
        # Not a compressed file that we're going to try to extract
        return

    if verbose:
        print('Extracting {}'.format(name))

    base, ext = m.groups()

    try:
        if ext == 'zip':
            cfile = ZipFile(name)
        elif ext == 'gz':
            cfile = gzip.open(name, 'r')
        else:
            cfile = tarfile.open(name, 'r:*')
    except (IOError, tarfile.ReadError, BadZipfile):
        print('Error reading file for extraction {}'.format(name))
        return

    try:
        # extract to a dir of its own to start with.
        extract_dir = datetime.datetime.now().isoformat()
        if ext == 'gz':
            os.makedirs(extract_dir)
            f = open(os.path.join(extract_dir, base), 'wb')
            chunk = 1024*8
            buff = cfile.read(chunk)
            while buff:
                f.write(buff)
                buff = cfile.read(chunk)
            f.close()
        else:
            cfile.extractall(extract_dir)
    except OSError:
        print('Error extracting {}'.format(name))
        return
    finally:
        cfile.close()

    # If there's no directory at all, then it was probably an empty archive
    if not os.path.isdir(extract_dir):
        return

    try:
        extract_files = os.listdir(extract_dir)
        if len(extract_files) == 1 and extract_files[0] == base:
            # If there's only one file/dir in the dir, and that file/dir
            # matches the base name of the archive, move the file/dir back one
            # into the parent dir and remove the extract directory.
            # The classic tar.gz -> dir and txt.gz -> file cases.
            shutil.move(os.path.join(extract_dir, extract_files[0]), start_dir)
            shutil.rmtree(extract_dir)

            # Set the name of the extracted dir for recursive decompression
            extract_dir = extract_files[0]
        else:
            # If there's more than one file in the dir, or if that file/dir
            # doesn't match the base name of the archive rename the extract dir
            # to the basename of the archive.
            # The 'barfing files all over pwd' case, the 'archive contains
            # var/log/blah/blah' case, and the 'archive contains a single,
            # differently named file' case.
            shutil.move(os.path.join(extract_dir), base)

            # Set the name of the extracted dir for recursive decompression
            extract_dir = base
    except shutil.Error as e:
        print('Error arranging directories:')
        print(e)
        return

    # See if there's anything left to do
    if not os.path.isdir(extract_dir):
        return

    # Get a list of files for recursive decompression
    sub_files = os.listdir(extract_dir)

    # Extract anything compressed that this archive had in it.
    os.chdir(extract_dir)
    for sub_file in sub_files: zdsplode(sub_file)
    os.chdir(start_dir)

