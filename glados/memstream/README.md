# About

This code tries to replace the memstream dependency from the original code base, which had to load the linux libc for the functionalities.

Originally this was used to re-implement the function calls under MacOS, but should also work with Windows.

Code comes originally from the libvisio2svg code at:

https://github.com/kakwa/libvisio2svg/blob/OSX_SUPPORT/deps/memstream-0.1/memstream.c

# Compile
gcc -o memstream.o -c memstream.c   

# Build library 
g++ -dynamiclib -undefined suppress  memstream.o -o memstream.dylib

Then just put the library at the same location of other libraries like whisper, and refer it with its name.
