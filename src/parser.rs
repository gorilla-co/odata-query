use crate::ast::CommonExpr;
use crate::chumsky_ext;
use chumsky::prelude::*;

pub fn parser() -> impl Parser<char, CommonExpr, Error = Simple<char>> {
    let null = text::keyword("null").to(CommonExpr::Null).labelled("null");

    let bool = chumsky_ext::keyword_ignore_ascii_case("true")
        .to(CommonExpr::Boolean(true))
        .or(chumsky_ext::keyword_ignore_ascii_case("false").to(CommonExpr::Boolean(false)))
        .labelled("boolean");

    // Integers
    let sign = one_of("+-").or_not();
    let _signed_int = sign
        .chain::<char, _, _>(filter(|c: &char| c.is_ascii_digit()).repeated().at_least(1))
        .collect();
    let int = _signed_int
        .clone()
        .map(|val: String| CommonExpr::Integer(val.parse().unwrap()))
        .labelled("int");

    // Floats
    let nan = text::keyword("NaN").to(CommonExpr::Float(f64::NAN));
    let inf = text::keyword("INF").to(CommonExpr::Float(f64::INFINITY));
    let neg_inf = just('-')
        .then(text::keyword("INF"))
        .to(CommonExpr::Float(f64::NEG_INFINITY));
    let exp = one_of("eE").chain(_signed_int.clone());
    let frac = just('.').chain(filter(|c: &char| c.is_ascii_digit()).repeated().at_least(1));
    let float_lit = _signed_int
        .clone()
        .chain::<char, _, _>(frac.or_not().flatten())
        .chain::<char, _, _>(exp.or_not().flatten())
        .collect::<String>()
        .map(|val: String| CommonExpr::Float(val.parse().unwrap()));
    let float = choice((float_lit, nan, inf, neg_inf)).labelled("decimal");

    choice((null, bool, int, float)).then_ignore(end())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_null() {
        let p = parser();
        assert_eq!(p.parse("null"), Ok(CommonExpr::Null));
    }

    #[test]
    fn parse_boolean() {
        let p = parser();
        assert_eq!(p.parse("true"), Ok(CommonExpr::Boolean(true)));
        assert_eq!(p.parse("True"), Ok(CommonExpr::Boolean(true)));
        assert_eq!(p.parse("false"), Ok(CommonExpr::Boolean(false)));
        assert_eq!(p.parse("False"), Ok(CommonExpr::Boolean(false)));
    }

    #[test]
    fn parse_integer() {
        let p = parser();
        assert_eq!(p.parse("0"), Ok(CommonExpr::Integer(0)));
        assert_eq!(p.parse("123456789"), Ok(CommonExpr::Integer(123456789)));
        assert_eq!(p.parse("+123456789"), Ok(CommonExpr::Integer(123456789)));
        assert_eq!(p.parse("-123456789"), Ok(CommonExpr::Integer(-123456789)));
    }

    #[test]
    fn parse_float() {
        let p = parser();
        assert_eq!(p.parse("0.1"), Ok(CommonExpr::Float(0.1)));
        assert_eq!(p.parse("-0.1"), Ok(CommonExpr::Float(-0.1)));
        assert_eq!(p.parse("1e10"), Ok(CommonExpr::Float(1e10)));
        assert_eq!(p.parse("-1e10"), Ok(CommonExpr::Float(-1e10)));
        assert_eq!(p.parse("1e-10"), Ok(CommonExpr::Float(1e-10)));
        assert_eq!(p.parse("1E-10"), Ok(CommonExpr::Float(1e-10)));
        assert_eq!(p.parse("123.456e10"), Ok(CommonExpr::Float(123.456e10)));
        assert_eq!(p.parse("INF"), Ok(CommonExpr::Float(f64::INFINITY)));
        assert_eq!(p.parse("-INF"), Ok(CommonExpr::Float(f64::NEG_INFINITY)));

        // NaN never tests equal:
        match p.parse("NaN") {
            Ok(CommonExpr::Float(nan)) => assert!(nan.is_nan()),
            _ => assert!(false),
        };
    }
}
