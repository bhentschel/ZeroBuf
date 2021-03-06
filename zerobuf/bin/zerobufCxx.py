#!/usr/bin/env python

# TODO:
# * configurable allocator class name
# WIP:
# * nested static/dynamic tables
# * get/setJSON()

# UUID is MD5 hash of namespace::namespace[<cxxtype>|<cxxtype>*|<cxxtype><size>]
#
# Zerobuf binary format is:
#   [dynamic storage headers][static storage][dynamic storage]
#     dynamic storage headers: 8b offset, 8b size
#       for all dynamic arrays in order of spec
#       later dynamic nested classes
#     static storage: 1,2,4,8,16b (* static array size)
#       for all static arrays and variables in order of spec
#       see emit.types for size
#       later also for static nested classes
#     dynamic storage layout is an implementation detail of the Allocator
#
# String arrays '[string]' are stored as an array of 'offset, size' tuples.

import argparse
import hashlib
from pyparsing import *
from sys import stdout, stderr, argv, exit
from os import path

fbsBaseType = oneOf( "int uint float double byte short ubyte ushort ulong uint8_t uint16_t uint32_t uint64_t uint128_t int8_t int16_t int32_t int64_t bool string" )

# namespace foo.bar
fbsNamespaceName = Group( ZeroOrMore( Word( alphanums ) + Suppress( '.' )) +
                          Word( alphanums ))
fbsNamespace = Group( Keyword( "namespace" ) + fbsNamespaceName +
                      Suppress( ';' ))

# enum EventDirection : ubyte { Subscriber, Publisher, Both }
fbsEnumValue = ( Word( alphanums ) + Suppress( Optional( ',' )))
fbsEnum = Group( Keyword( "enum" ) + Word( alphanums ) + Suppress( ':' ) +
                 fbsBaseType + Suppress( '{' ) + OneOrMore( fbsEnumValue ) +
                 Suppress( '}' ))

# value:[type]; entries in table
fbsType = ( fbsBaseType ^ Word( alphanums ))
fbsTableArray = ( ( Literal( '[' ) + fbsType + Literal( ']' )) ^
                  ( Literal( '[' ) + fbsType + Literal( ':' ) + Word( nums ) +
                    Literal( ']' )) )
fbsTableValue = ( fbsType ^ fbsTableArray )
fbsTableEntry = Group( Word( alphanums+"_" ) + Suppress( ':' ) + fbsTableValue +
                       Suppress( ';' ))
fbsTableSpec = ZeroOrMore( fbsTableEntry )

# table Foo { entries }
fbsTable = Group( Keyword( "table" ) + Word( alphas, alphanums ) +
                  Suppress( '{' ) + fbsTableSpec + Suppress( '}' ))

# root_type foo;
fbsRootType = Group( Keyword( "root_type" ) + Word( alphanums ) +
                     Suppress( ";" ))

# namespace, table(s), root_type
fbsObject = ( Optional( fbsNamespace ) + ZeroOrMore( fbsEnum ) +
              OneOrMore( fbsTable ) + Optional( fbsRootType ))

fbsComment = cppStyleComment
fbsObject.ignore( fbsComment )

#fbsTableArray.setDebug()
#fbsTableValue.setDebug()
#fbsTableEntry.setDebug()

def emitFunction( retVal, function, body, static=False, explicit=False ):
    if retVal: # '{}'-less body
        header.write( "    {0}{1} {2};\n".format("static " if static else "", retVal, function))
        impl.write( "template< class Alloc >\ninline " + retVal + " " + emit.table +
                    "Base< Alloc >::" + function + "\n{\n    " + body +
                    "\n}\n\n" )
    else:      # ctor '[initializer list]{ body }'
        header.write( "    {0}{1};\n".format("explicit " if explicit else "", function))
        impl.write( "template< class Alloc >\ninline " + emit.table +
                    "Base< Alloc >::" + function + "\n    " + body + "\n\n" )

def isDynamic( spec ):
    isString = ( spec[1] == "string" )
    if len( spec ) == 2 and not isString:
        return False
    if len( spec ) == 6: # static array
        return False
    return True

def countDynamic( specs ):
    numDynamic = 0
    for spec in specs:
        if isDynamic( spec ):
            numDynamic += 1
    return numDynamic

def emitDynamic( spec ):
    if not isDynamic( spec ):
        return;

    cxxName = spec[0][0].upper() + spec[0][1:]
    cxxtype = "char"
    isString = ( spec[1] == "string" )
    if not isString:
        cxxtype = emit.types[ spec[2] ][1]
    header.write( "    typedef ::zerobuf::Vector< " + cxxtype + " > " + cxxName + ";\n" )
    header.write( "    typedef ::zerobuf::ConstVector< " + cxxtype + " > Const" + cxxName + ";\n" )
    emit.md5.update( cxxtype.encode('utf-8') + b"Vector" )

    # non-const, const pointer
    emitFunction( "typename " + emit.table + "Base< Alloc >::" + cxxName,
                  "get" + cxxName + "()",
                  "return " + cxxName + "( getAllocator(), " + str( emit.currentDyn ) + " );" )
    emitFunction( "typename " + emit.table + "Base< Alloc >::Const" + cxxName,
                  "get" + cxxName + "() const",
                  "return Const" + cxxName + "( getAllocator(), " + str( emit.currentDyn ) + " );" )
    emitFunction( "void",
                  "set" + cxxName + "( " + cxxtype +
                  " const * value, size_t size )",
                  "_setZerobufArray( value, size * sizeof( " + cxxtype +
                  " ), " + str( emit.currentDyn ) + " );" )
    # vector
    emitFunction( "std::vector< " + cxxtype + " >",
                  "get" + cxxName + "Vector() const",
                  "const Const" + cxxName + "& vec = get" + cxxName + "();\n    return std::vector< " + cxxtype +
                  " >( vec.data(), vec.data() + vec.size( ));" )
    emitFunction( "void",
                  "set" + cxxName + "( const std::vector< " +
                  cxxtype + " >& value )",
                  "_setZerobufArray( value.data(), value.size() * sizeof( " + cxxtype +
                  " ), " + str( emit.currentDyn ) + " );" )
    # string
    emitFunction( "std::string",
                  "get" + cxxName + "String() const",
                  "const uint8_t* ptr = getAllocator()->template getDynamic< " +
                  "const uint8_t >( " + str( emit.currentDyn ) + " );\n" +
                  "    return std::string( ptr, ptr + " +
                  "getAllocator()->template getItem< uint64_t >( " +
                  str( emit.offset + 8 ) + " ));" )
    emitFunction( "void",
                  "set" + cxxName + "( const std::string& value )",
                  "_setZerobufArray( value.c_str(), value.length(), " +
                  str( emit.currentDyn ) + " );" )
    # schema entry
    emit.entries.append("std::make_tuple(\"{0}\", \"{1}\", {2}, {3}, {4} )".format(spec[0], cxxtype, emit.currentDyn, emit.offset + 8, "false"))

    emit.offset += 16 # 8b offset, 8b size
    emit.currentDyn += 1
    header.write( "\n" )
    impl.write( "\n" )

def emitVariable( spec ):
    if( len( spec ) != 2 and len( spec ) != 6 ) or spec[1] == "string":
        return

    if len( spec ) == 2: # variable
        cxxName = spec[0][0].upper() + spec[0][1:]
        cxxtype = emit.types[ spec[1] ][1]
        emit.md5.update( cxxtype.encode('utf-8') )
        emitFunction( cxxtype, "get" + cxxName + "() const",
                      "return getAllocator()->template getItem< " + cxxtype +
                      " >( " + str( emit.offset ) + " );" )
        emitFunction( "void",
                      "set"  + cxxName + "( " + cxxtype + " value )",
                      "getAllocator()->template getItem< " + cxxtype + " >( " +
                      str( emit.offset ) + " ) = value;" )

        # schema entry
        emit.entries.append("std::make_tuple(\"{0}\", \"{1}\", {2}, {3}, {4} )".format(spec[0], cxxtype, emit.offset, 0, "true"))
        emit.offset += emit.types[ spec[1] ][0]
    else: # static array
        cxxName = spec[0][0].upper() + spec[0][1:]
        cxxtype = emit.types[ spec[2] ][1]
        nElems = spec[4]
        emit.md5.update( (cxxtype + nElems).encode('utf-8') )
        nBytes = int(emit.types[ spec[2] ][0]) * int(nElems)
        emitFunction( cxxtype + "*", "get" + cxxName + "()",
                      "return getAllocator()->template getItemPtr< " + cxxtype +
                      " >( " + str( emit.offset ) + " );" )
        emitFunction( "const " + cxxtype + "*",
                      "get" + cxxName + "() const",
                      "return getAllocator()->template getItemPtr< " + cxxtype +
                      " >( " + str( emit.offset ) + " );" )
        emitFunction( "std::vector< " + cxxtype + " >",
                      "get" + cxxName + "Vector() const",
                      "const " + cxxtype + "* ptr = getAllocator()->template " +
                      "getItemPtr< " + cxxtype + " >( " + str( emit.offset ) +
                      " );\n    return std::vector< " + cxxtype +
                      " >( ptr, ptr + " + nElems + " );" )
        emitFunction( "void",
                      "set"  + cxxName + "( " + cxxtype + " value[ " +
                      spec[4] + " ] )",
                      "::memcpy( getAllocator()->template getItemPtr< " +
                      cxxtype + " >( " + str( emit.offset ) + " ), value, " +
                      spec[4] + " * sizeof( " + cxxtype + " ));" )
        emitFunction( "void",
                      "set" + cxxName + "( const std::vector< " +
                      cxxtype + " >& value )",
                      "if( " + str( nElems ) + " >= value.size( ))\n" +
                      "        ::memcpy( getAllocator()->template getItemPtr<" +
                      cxxtype + ">( " + str( emit.offset ) +
                      " ), value.data(), value.size() * sizeof( " + cxxtype +
                      "));" )
        emitFunction( "void",
                      "set" + cxxName + "( const std::string& value )",
                      "if( " + str( nBytes ) + " >= value.length( ))\n" +
                      "        ::memcpy( getAllocator()->template getItemPtr<" +
                      cxxtype + ">( " + str( emit.offset ) +
                      " ), value.data(), value.length( ));" )
        # schema entry
        emit.entries.append("std::make_tuple(\"{0}\", \"{1}\", {2}, {3}, {4} )".format(spec[0], cxxtype, emit.offset, nElems, "true"))
        emit.offset += nBytes
    header.write( "\n" )
    impl.write( "\n" )


def emit():
    emit.namespace = ""
    emit.offset = 0
    emit.numDynamic = 0;
    emit.currentDyn = 0;
    emit.types = { "int" : ( 4, "int32_t" ),
                   "uint" : ( 4, "uint32_t" ),
                   "float" : ( 4, "float" ),
                   "double" : ( 8, "double" ),
                   "byte" : ( 1, "int8_t" ),
                   "short" : ( 2, "int16_t" ),
                   "ubyte" : ( 1, "uint8_t" ),
                   "ushort" : ( 2, "uint16_t" ),
                   "ulong" : ( 8, "uint64_t" ),
                   "uint8_t" : ( 1, "uint8_t" ),
                   "uint16_t" : ( 2, "uint16_t" ),
                   "uint32_t" : ( 4, "uint32_t" ),
                   "uint64_t" : ( 8, "uint64_t" ),
                   "uint128_t" : ( 16, "servus::uint128_t" ),
                   "int8_t" : ( 1, "int8_t" ),
                   "int16_t" : ( 2, "int16_t" ),
                   "int32_t" : ( 4, "int32_t" ),
                   "int64_t" : ( 8, "int64_t" ),
                   "bool" : ( 1, "bool" ),
                   "string" : ( 1, "char*" ),
    }
    emit.entries = []

    def namespace():
        for namespace in emit.namespace:
            header.write( "}\n" )
            impl.write( "}\n" )
        emit.namespace = item[1]
        for namespace in emit.namespace:
            header.write( "namespace " + namespace + "\n{\n" )
            impl.write( "namespace " + namespace + "\n{\n" )

    def enum():
        emit.types[ item[1] ] = ( 4, item[1] )
        header.write( "enum " + item[1] + "\n{\n" )
        for enumValue in item[3:]:
            header.write( "    " + item[1] + "_" + enumValue + ",\n" )
        header.write( "};\n\n" )

    def table():
        emit.types[ item[1] ] = ( 4, item[1] )
        emit.offset = 4 # 4b version header in host endianness
        emit.numDynamic = countDynamic( item[2:] )
        emit.currentDyn = 0
        emit.table = item[1]
        emit.md5 = hashlib.md5()
        for namespace in emit.namespace:
            emit.md5.update( namespace.encode('utf-8') + b"::" )
        emit.md5.update( item[1].encode('utf-8') )

        # class header
        header.write( "template< class Alloc = zerobuf::NonMovingAllocator >\n"+
                      "class " + item[1] + "Base : public zerobuf::Zerobuf\n" +
                      "{\npublic:\n" )

        # member access
        for member in item[2:]:
            emitDynamic( member )
        for member in item[2:]:
            emitVariable( member )
        # ctors, dtor and assignment operator
        if emit.offset == 4: # OPT: table has no data
            emit.offset = 0
            header.write( "    " + item[1] + "Base() : Zerobuf() {}\n" )
            header.write( "    " + item[1] + "Base( const " + item[1] +
                          "Base& ) : Zerobuf() {}\n" )
            header.write( "    virtual ~" + item[1] + "Base() {}\n\n" )
            header.write( "    " + item[1] + "Base& operator = ( const " +
                          item[1] + "Base& ) { return *this; }\n\n" )
        else:
            emitFunction( None, item[1] + "Base()",
                          ": zerobuf::Zerobuf( new Alloc( " +
                          str( emit.offset ) + ", " + str( emit.currentDyn ) +
                          " ))\n{}\n" )
            emitFunction( None,
                          item[1] + "Base( const ::zerobuf::Zerobuf& from )",
                          ": zerobuf::Zerobuf( new Alloc( *static_cast< const Alloc* >(from.getAllocator( ))))\n{}",
                          explicit=True)
            emitFunction( None,
                          item[1] + "Base( const " + item[1] + "Base& from )",
                          ": zerobuf::Zerobuf( new Alloc( *static_cast< const Alloc* >(from.getAllocator( ))))\n{}" )
            header.write( "    virtual ~" + item[1] + "Base() {}\n\n" )

            header.write( "    " + item[1] + "Base& operator = ( const " + item[1] + "Base& rhs )\n"+
                          "        { ::zerobuf::Zerobuf::operator = ( rhs ); return *this; }\n\n" )

        # introspection
        header.write( "    static bool isEmptyZerobuf() { return " +
                   str( emit.offset == 0 ).lower() + "; }\n" )
        header.write( "    static bool isStaticZerobuf() { return " +
                   str( emit.numDynamic == 0 ).lower() + "; }\n" )

        # zerobufType
        digest = emit.md5.hexdigest()
        high = digest[ 0 : len( digest ) - 16 ]
        low  = digest[ len( digest ) - 16: ]
        zerobufType = "servus::uint128_t( 0x{0}ull, 0x{1}ull )".format(high, low)
        header.write( "    servus::uint128_t getZerobufType() const override\n" +
                      "        { return " + zerobufType + "; }\n" )
        header.write( "\n" )

        # schema
        schema = "{{ {0}, {1},\n        {2},\n        {{\n         {3}\n         }} }}".format(emit.offset, emit.currentDyn, zerobufType, ',\n         '.join(emit.entries))
        emitFunction( "::zerobuf::Schema",
                      "schema()",
                      "return " + schema + ";", True )
        header.write( "    ::zerobuf::Schema getSchema() const override { return schema(); }\n" )
        header.write( "\n" )

        # private implementation
        header.write( "private:\n" )
        # static size + num dynamic member introspection:
        # header.write( "    static const size_t ZEROBUF_STATIC_SIZE = " +
        #            str( emit.offset ) + ";\n" )
        # header.write( "    static const size_t ZEROBUF_NUM_DYNAMIC = " +
        #            str( emit.numDynamic ) + ";\n" )
        header.write( "};\n\n" )
        header.write( "typedef " + item[1] +
                      "Base< ::zerobuf::NonMovingAllocator > " + item[1] +
                      ";\n" )
        header.write( "\n" )
        impl.write( "\ntemplate class " + item[1] +
                    "Base< ::zerobuf::NonMovingAllocator >;\n" )

    def root_type():
        header.write( "" )

    rootOptions = { "namespace" : namespace,
                    "enum" : enum,
                    "table" : table,
                    "root_type" : root_type,
                    }

    header.write( "// Generated by zerobufCxx.py\n\n" )
    header.write( "#pragma once\n" )
    header.write( "#include <zerobuf/ConstVector.h>\n" )
    header.write( "#include <zerobuf/NonMovingAllocator.h>\n" )
    header.write( "#include <zerobuf/Schema.h>\n" )
    header.write( "#include <zerobuf/Vector.h>\n" )
    header.write( "#include <zerobuf/Zerobuf.h>\n" )
    header.write( "\n" )
    impl.write( "// Generated by zerobufCxx.py\n\n" )

    for item in schema:
        rootOptions[ item[0] ]()

    for namespace in emit.namespace:
        header.write( "}\n" )
        impl.write( "}\n" )

    header.write( "\n#include \"" + headerbase + ".ipp\"\n\n" )

if __name__ == "__main__":
    if len(argv) < 2 :
        stderr.write("ERROR - " + argv[0] + " - too few input arguments!")
        exit(-1)
    
    parser = argparse.ArgumentParser( description =
                                      "zerobufCxx.py: A zerobuf C++ code generator for extended flatbuffers schemas" )
    parser.add_argument( "files", nargs = "*" )
    parser.add_argument( '-o', '--outputdir', action='store', default = "",
                         help = "Prefix directory for all generated files.")

    # Parse, interpret and validate arguments
    args = parser.parse_args()
    if len(args.files) == 0 :
        stderr.write("ERROR - " + argv[0] + " - no input .fbs files given!")
        exit(-1)
    
    for file in args.files:
        basename = path.splitext( file )[0]
        headerbase = path.basename( basename )
        if args.outputdir:
            if args.outputdir == '-':
                header = stdout
                impl = stdout
            else:
                header = open( args.outputdir + "/" + headerbase + ".h", 'w' )
                impl = open( args.outputdir + "/" + headerbase + ".ipp", 'w' )
        else:
            header = open( basename + ".h" , 'w' )
            impl = open( basename + ".ipp" , 'w' )

        schema = fbsObject.parseFile( file )

        # import pprint
        # pprint.pprint( schema.asList( ))
        emit()
