# This is a pygame2exe script I found on the internet

# This will create a dist directory containing the executable file, all the data
# directories. All Libraries will be bundled in executable file.
#
# Run the build process by entering 'pygame2exe.py' or
# 'python pygame2exe.py' in a console prompt.
#
# To build exe, python, pygame, and py2exe have to be installed. After
# building exe none of this libraries are needed.
#Please Note have a backup file in a different directory as if it crashes you 
#will loose it all!(I lost 6 months of work because I did not do this)


 
try:
    from distutils.core import setup
    import py2exe, pygame
    from modulefinder import Module
    import glob, fnmatch
    import sys, os, shutil
    import operator
    import shutil
    import zipfile

except ImportError, message:
    raise SystemExit,  "Unable to load module. %s" % message
 
#hack which fixes the pygame mixer and pygame font
origIsSystemDLL = py2exe.build_exe.isSystemDLL # save the orginal before we edit it
def isSystemDLL(pathname):
    # checks if the freetype and ogg dll files are being included
    if os.path.basename(pathname).lower() in ("libfreetype-6.dll", "libogg-0.dll","sdl_ttf.dll"): # "sdl_ttf.dll" added by arit.
            return 0
    return origIsSystemDLL(pathname) # return the orginal function
py2exe.build_exe.isSystemDLL = isSystemDLL # override the default function with this one
 
class pygame2exe(py2exe.build_exe.py2exe):
    #This hack make sure that pygame default font is copied: no need to modify code for specifying default font
    def copy_extensions(self, extensions):
        #Get pygame default font
        pygamedir = os.path.split(pygame.base.__file__)[0]
        pygame_default_font = os.path.join(pygamedir, pygame.font.get_default_font())

 
        #Add font to list of extension to be copied
        extensions.append(Module("pygame.font", pygame_default_font))
        #Add a Tk DLL as well
        #extensions.append(Module("_tkinter", "C:/Python27/DLLs/tk85.dll", "C:/Python27/DLLs/tcl85.dll"))

        py2exe.build_exe.py2exe.copy_extensions(self, extensions)

    # This hack removes tk85.dll from the list of dlls that don't get bundled, since it can be bundled.
    def copy_dlls(self, dlls):
        # copy needed dlls where they belong.
        print "*** copy dlls ***"
        self.dlls_in_exedir.remove('tk85.dll') # The added line
        if self.bundle_files < 3:
            self.copy_dlls_bundle_files(dlls)
            return
        # dlls belong into the lib_dir, except those listed in dlls_in_exedir,
        # which have to go into exe_dir (pythonxy.dll, w9xpopen.exe).
        for dll in dlls:
            base = os.path.basename(dll)
            if base.lower() in self.dlls_in_exedir:
                # These special dlls cannot be in the lib directory,
                # they must go into the exe directory.
                dst = os.path.join(self.exe_dir, base)
            else:
                dst = os.path.join(self.lib_dir, base)
            _, copied = self.copy_file(dll, dst, preserve_mode=0)
            if not self.dry_run and copied and base.lower() == python_dll.lower():
                # If we actually copied pythonxy.dll, we have to patch it.
                #
                # Previously, the code did it every time, but this
                # breaks if, for example, someone runs UPX over the
                # dist directory.  Patching an UPX'd dll seems to work
                # (no error is detected when patching), but the
                # resulting dll does not work anymore.
                #
                # The function restores the file times so
                # dependencies still work correctly.
                self.patch_python_dll_winver(dst)

            self.lib_files.append(dst)
 
class BuildExe:
    def __init__(self, scriptname):
        #Name of starting .py
        self.script = scriptname

        #Name of program
        self.project_name = "Rebirth Item Tracker"
 
        #Project url
        self.project_url = "about:none"
 
        #Version of program
        self.project_version = ""
 
        #License of the program
        self.license = "MyApps License"
 
        #Auhor of program
        self.author_name = "Hyphen-ated, Brett824, Various Others"
        self.author_email = ""
        self.copyright = "Copyright (c) 2015 Hyphen-ated and Brett824"
 
        #Description
        self.project_description = ""
 
        #Icon file (None will use pygame default icon)
        self.icon_file = None
 
        #Extra files/dirs copied to game
        self.extra_datas = []
 
        #Extra/excludes python modules
        self.extra_modules = []
        self.exclude_modules = []
        
        #DLL Excludes
        self.exclude_dll = ['w9xpopen.exe', 'libogg-0.dll', 'libvorbis-0.dll', 'libvorbisfile-3.dll', 'smpeg.dll']
        #python scripts (strings) to be included, separated by a comma
        self.extra_scripts = []
 
        #Zip file name (None will bundle files in exe instead of zip file)
        self.zipfile_name = "library/library.zip"

        #Dist directory
        self.dist_dir ='dist'

    ## Code from DistUtils tutorial at http://wiki.python.org/moin/Distutils/Tutorial
    ## Originally borrowed from wxPython's setup and config files
    def opj(self, *args):
        path = os.path.join(*args)
        return os.path.normpath(path)
 
    def find_data_files(self, srcdir, *wildcards, **kw):
        # get a list of all files under the srcdir matching wildcards,
        # returned in a format to be used for install_data
        def walk_helper(arg, dirname, files):
            if '.svn' in dirname:
                return
            names = []
            lst, wildcards = arg
            for wc in wildcards:
                wc_name = self.opj(dirname, wc)
                for f in files:
                    filename = self.opj(dirname, f)
 
                    if fnmatch.fnmatch(filename, wc_name) and not os.path.isdir(filename):
                        names.append(filename)
            if names:
                lst.append( (dirname, names ) )
 
        file_list = []
        recursive = kw.get('recursive', True)
        if recursive:
            os.path.walk(srcdir, walk_helper, (file_list, wildcards))
        else:
            walk_helper((file_list, wildcards),
                        srcdir,
                        [os.path.basename(f) for f in glob.glob(self.opj(srcdir, '*'))])
        return file_list
 
    def run(self):
        if os.path.isdir(self.dist_dir): #Erase previous destination dir
            shutil.rmtree(self.dist_dir)
        
        #Use the default pygame icon, if none given
        if self.icon_file == None:
            path = os.path.split(pygame.__file__)[0]
            self.icon_file = os.path.join(path, 'pygame.ico')
 
        #List all data files to add
        extra_datas = []
        for data in self.extra_datas:
            if os.path.isdir(data):
                extra_datas.extend(self.find_data_files(data, '*'))
            else:
                extra_datas.append(('.', [data]))
        
        setup(
            cmdclass = {'py2exe': pygame2exe},
            version = self.project_version,
            description = self.project_description,
            name = self.project_name,
            url = self.project_url,
            author = self.author_name,
            author_email = self.author_email,
            license = self.license,
 
            # targets to build
            windows = [{
                'script': self.script,
                'icon_resources': [(0, self.icon_file)],
                'copyright': self.copyright
            }],
            options = {'py2exe': {'optimize': 2, 'bundle_files': 1, 'compressed': True, \
                                  'excludes': self.exclude_modules, 'packages': self.extra_modules, \
                                  'dll_excludes': self.exclude_dll,
                                  'includes': self.extra_scripts} },
            zipfile = self.zipfile_name,
            data_files = extra_datas,
            dist_dir = self.dist_dir
            )
        
        if os.path.isdir('build'): #Clean up build dir
            shutil.rmtree('build')


if __name__ == '__main__':
    # pull the name of the python script we're turning into an exe from argv,
    # then put on 'py2exe' because this hacky thing needs it
    script = sys.argv[-1]
    sys.argv=sys.argv[:-1]
    sys.argv.append('py2exe')
    BuildExe(script).run() #Run generation




