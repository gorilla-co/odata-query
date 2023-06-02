use crate::ast::{CommonExpr, Literal};
use nom::branch::alt;
use nom::bytes::complete::{is_not, tag, tag_no_case};
use nom::character::complete::{char, digit1, one_of};
use nom::combinator::{cut, map, opt, recognize, value, verify};
use nom::error::{Error, ParseError};
use nom::multi::many0;
use nom::sequence::{delimited, pair, tuple};
use nom::IResult;
use nom::ParseTo;

pub fn parse_float(inp: &str) -> IResult<&str, f64> {
    let (i, float_str) = recognize(verify(
        tuple((
            opt(one_of("+-")),
            digit1,
            opt(pair(char('.'), opt(digit1))),
            opt(tuple((one_of("eE"), opt(one_of("+-")), cut(digit1)))),
        )),
        // We need at least a fraction or an exponent for a valid float
        |(_, _, frac, exp)| frac.is_some() || exp.is_some(),
    ))(inp)?;

    match float_str.parse_to() {
        Some(f) => Ok((i, f)),
        None => Err(nom::Err::Error(Error::from_error_kind(
            i,
            nom::error::ErrorKind::Float,
        ))),
    }
}

pub fn parse_string(inp: &str) -> IResult<&str, String> {
    let part = alt((
        is_not("'"),
        // Double SQUOTE within a string escapes to a single SQUOTE
        value("'", tag("''")),
    ));

    let str_parts = delimited(char('\''), many0(part), char('\''));
    map(str_parts, |p| p.join(""))(inp)
}

pub fn parse_literal(inp: &str) -> IResult<&str, Literal> {
    let null = value(Literal::Null, tag("null"));

    let bool = alt((
        value(Literal::Boolean(true), tag_no_case("true")),
        value(Literal::Boolean(false), tag_no_case("false")),
    ));

    let int = map(nom::character::complete::i64, Literal::Integer);
    let float = alt((
        map(parse_float, Literal::Float),
        value(Literal::Float(f64::NAN), tag("NaN")),
        value(Literal::Float(f64::INFINITY), tag("INF")),
        value(Literal::Float(f64::NEG_INFINITY), tag("-INF")),
    ));

    let string = map(parse_string, Literal::String);

    alt((null, bool, string, float, int))(inp)
}

pub fn parse(odata_query: &str) -> IResult<&str, CommonExpr> {
    (map(parse_literal, CommonExpr::Literal))(odata_query)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn assert_parsed_to<T>(result: IResult<&str, T>, exp: T)
    where
        T: std::fmt::Debug + std::cmp::PartialEq,
    {
        assert!(result.is_ok());
        match result {
            Ok((rest, node)) => {
                assert!(rest.is_empty(), "Unparsed input: {rest}");
                assert_eq!(node, exp);
            }
            _ => panic!("Shouldn't occur"),
        }
    }

    #[test]
    fn parse_null() {
        assert_parsed_to(parse_literal("null"), Literal::Null);
    }

    #[test]
    fn parse_boolean() {
        assert_parsed_to(parse_literal("true"), Literal::Boolean(true));
        assert_parsed_to(parse_literal("True"), Literal::Boolean(true));
        assert_parsed_to(parse_literal("false"), Literal::Boolean(false));
        assert_parsed_to(parse_literal("False"), Literal::Boolean(false));
    }

    #[test]
    fn parse_integer() {
        assert_parsed_to(parse_literal("0"), Literal::Integer(0));
        assert_parsed_to(parse_literal("123456789"), Literal::Integer(123456789));
        assert_parsed_to(parse_literal("+123456789"), Literal::Integer(123456789));
        assert_parsed_to(parse_literal("-123456789"), Literal::Integer(-123456789));
    }

    #[test]
    fn parse_float() {
        assert_parsed_to(parse_literal("0.1"), Literal::Float(0.1));
        assert_parsed_to(parse_literal("-0.1"), Literal::Float(-0.1));
        assert_parsed_to(parse_literal("1e10"), Literal::Float(1e10));
        assert_parsed_to(parse_literal("-1e10"), Literal::Float(-1e10));
        assert_parsed_to(parse_literal("1e-10"), Literal::Float(1e-10));
        assert_parsed_to(parse_literal("1E-10"), Literal::Float(1e-10));
        assert_parsed_to(parse_literal("123.456e10"), Literal::Float(123.456e10));
        assert_parsed_to(parse_literal("INF"), Literal::Float(f64::INFINITY));
        assert_parsed_to(parse_literal("-INF"), Literal::Float(f64::NEG_INFINITY));

        // NaN never tests equal:
        match parse_literal("NaN") {
            Ok(("", Literal::Float(nan))) => assert!(nan.is_nan()),
            _ => assert!(false),
        };
    }

    #[test]
    fn parse_string() {
        assert_parsed_to(
            parse_literal("'hello world'"),
            Literal::String("hello world".to_string()),
        );
        assert_parsed_to(parse_literal("''"), Literal::String("".to_string()));
        assert_parsed_to(
            parse_literal("'g''day sir'"),
            Literal::String("g'day sir".to_string()),
        );
    }
}
