
/* Copyright (c) 2015, Human Brain Project
 *                     Daniel Nachbaur <danielnachbaur@epfl.ch>
 */


#include <testSchema.h>

#define SETVALUES(type, name) \
    const std::vector< type > name##Vector { type(1), type(1), type(2), type(3) }; \
    const type name##value( 42 ); \
    \
    object.set##name##dynamic( name##Vector ); \
    object.set##name##array( name##Vector ); \
    object.set##name##value( name##value );

#define TESTVALUES(type, name) \
    const std::vector< type > expected##name##Vector { type(1), type(1), type(2), type(3) }; \
    const type expected##name##value( 42 ); \
    \
    const std::vector< type >& name##Dynamic( object.get##name##dynamicVector( )); \
    const std::vector< type >& name##Array( object.get##name##arrayVector( )); \
    const type& name##Value( object.get##name##value( )); \
    \
    BOOST_CHECK_EQUAL_COLLECTIONS( expected##name##Vector.begin(), expected##name##Vector.end(),\
                                   name##Dynamic.begin(), name##Dynamic.end( )); \
    BOOST_CHECK_EQUAL_COLLECTIONS( expected##name##Vector.begin(), expected##name##Vector.end(),\
                                   name##Array.begin(), name##Array.end( )); \
    BOOST_CHECK_EQUAL( expected##name##value, name##Value );


test::TestSchema getTestObject()
{
    test::TestSchema object;
    SETVALUES(int32_t, Int);
    SETVALUES(uint32_t, Uint);
    SETVALUES(float, Float);
    SETVALUES(double, Double);
    SETVALUES(int8_t, Byte);
    SETVALUES(int16_t, Short);
    SETVALUES(uint8_t, Ubyte);
    SETVALUES(uint16_t, Ushort);
    SETVALUES(uint64_t, Ulong);
    SETVALUES(uint8_t, Uint8_t);
    SETVALUES(uint16_t, Uint16_t);
    SETVALUES(uint32_t, Uint32_t);
    SETVALUES(uint64_t, Uint64_t);
    SETVALUES(servus::uint128_t, Uint128_t);
    SETVALUES(int8_t, Int8_t);
    SETVALUES(int16_t, Int16_t);
    SETVALUES(int32_t, Int32_t);
    SETVALUES(int64_t, Int64_t);
    object.setBoolvalue( true );
    object.setStringvalue( "testmessage" );
    return object;
}

void checkTestObject( const test::TestSchema& object )
{
    TESTVALUES(int32_t, Int);
    TESTVALUES(uint32_t, Uint);
    TESTVALUES(float, Float);
    TESTVALUES(double, Double);
    TESTVALUES(int8_t, Byte);
    TESTVALUES(int16_t, Short);
    TESTVALUES(uint8_t, Ubyte);
    TESTVALUES(uint16_t, Ushort);
    TESTVALUES(uint64_t, Ulong);
    TESTVALUES(uint8_t, Uint8_t);
    TESTVALUES(uint16_t, Uint16_t);
    TESTVALUES(uint32_t, Uint32_t);
    TESTVALUES(uint64_t, Uint64_t);
    TESTVALUES(servus::uint128_t, Uint128_t);
    TESTVALUES(int8_t, Int8_t);
    TESTVALUES(int16_t, Int16_t);
    TESTVALUES(int32_t, Int32_t);
    TESTVALUES(int64_t, Int64_t);
    BOOST_CHECK( object.getBoolvalue( ));
    BOOST_CHECK_EQUAL( object.getStringvalueString(), "testmessage" );
}
