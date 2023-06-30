use crate::ast::Literal;
use base64::{alphabet, engine, Engine as _};
use nom::branch::alt;
use nom::bytes::complete::{is_not, tag, tag_no_case, take_while, take_while_m_n};
use nom::character::complete::{char, digit1, one_of};
use nom::combinator::{cut, map, map_res, opt, recognize, value, verify};
use nom::error::{Error, ParseError};
use nom::multi::many0;
use nom::sequence::{delimited, pair, preceded, terminated, tuple};
use nom::IResult;
use nom::ParseTo;
use time::{Date, Duration, Month, OffsetDateTime, Time, UtcOffset};

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

// nom has its own `is_hex_digit`, but it only works on `u8`
fn is_hex_digit(c: char) -> bool {
    c.is_digit(16)
}

fn is_digit(c: char) -> bool {
    c.is_digit(10)
}

fn is_base64url_char(c: char) -> bool {
    c.is_ascii_alphanumeric() || c == '-' || c == '_' || c == '='
}

pub fn parse_guid(inp: &str) -> IResult<&str, String> {
    let (i, guid_str) = recognize(tuple((
        take_while_m_n(8, 8, is_hex_digit),
        char('-'),
        take_while_m_n(4, 4, is_hex_digit),
        char('-'),
        take_while_m_n(4, 4, is_hex_digit),
        char('-'),
        take_while_m_n(4, 4, is_hex_digit),
        char('-'),
        take_while_m_n(12, 12, is_hex_digit),
    )))(inp)?;

    Ok((i, guid_str.to_string()))
}

pub fn parse_year(inp: &str) -> IResult<&str, i32> {
    let parser = recognize(tuple((opt(char('-')), take_while_m_n(4, 4, is_digit))));

    // Infallible, as 4 digits always fit an i32
    map(parser, |s: &str| s.parse::<i32>().unwrap())(inp)
}

pub fn n_digits_between(inp: &str, n_digits: usize, min: u8, max: u8) -> IResult<&str, u8> {
    let digits = take_while_m_n(n_digits, n_digits, is_digit);

    verify(
        map(digits, |s: &str| s.parse::<u8>().unwrap()),
        |val: &u8| val >= &min && val <= &max,
    )(inp)
}

pub fn parse_month(inp: &str) -> IResult<&str, Month> {
    map_res(
        |i| n_digits_between(i, 2, 1, 12),
        |val| Month::try_from(val),
    )(inp)
}

pub fn parse_day(inp: &str) -> IResult<&str, u8> {
    n_digits_between(inp, 2, 1, 31)
}

pub fn parse_date(inp: &str) -> IResult<&str, Date> {
    // OData `year`s can be negative, conflicting with ISO8601.
    // So we don't use `time::*::parse`
    let parser = tuple((parse_year, char('-'), parse_month, char('-'), parse_day));

    map_res(parser, |(y, _, m, _, d)| Date::from_calendar_date(y, m, d))(inp)
}

pub fn parse_hour(inp: &str) -> IResult<&str, u8> {
    n_digits_between(inp, 2, 0, 24)
}

pub fn parse_minute(inp: &str) -> IResult<&str, u8> {
    n_digits_between(inp, 2, 0, 59)
}

pub fn parse_fractional_seconds(inp: &str) -> IResult<&str, u32> {
    // Parses the "fractionalSeconds" after the dot to an amount expressed in
    // nanoseconds
    let digits = take_while_m_n(1, 12, is_digit);

    // Since we want to express as nanoseconds, and this is the fractional part
    // of a number, we ensure we have exactly 9 digits before parsing:
    let nanos = map(digits, |d: &str| format!("{d:0<9.9}"));

    map(nanos, |s: String| s.parse::<u32>().unwrap())(inp)
}

pub fn parse_second(inp: &str) -> IResult<&str, (u8, u32)> {
    let parser = tuple((
        |i| n_digits_between(i, 2, 0, 59),
        opt(preceded(char('.'), parse_fractional_seconds)),
    ));

    map(parser, |(sec, frac)| (sec, frac.unwrap_or(0)))(inp)
}

pub fn parse_time(inp: &str) -> IResult<&str, Time> {
    let parser = tuple((
        parse_hour,
        char(':'),
        parse_minute,
        opt(preceded(char(':'), parse_second)),
    ));

    map_res(parser, |(h, _, m, s)| {
        let (sec, nano) = s.unwrap_or((0, 0));
        Time::from_hms_nano(h, m, sec, nano)
    })(inp)
}

pub fn parse_tzoffset(inp: &str) -> IResult<&str, UtcOffset> {
    alt((
        value(UtcOffset::UTC, tag_no_case("Z")),
        map(
            tuple((one_of("+-"), parse_hour, char(':'), parse_minute)),
            |(sign, h, _, m)| {
                let modif: i8 = match sign {
                    '+' => 1,
                    '-' => -1,
                    x => panic!("Unreachable: sign {x}"),
                };
                let hour = modif * TryInto::<i8>::try_into(h).unwrap();
                UtcOffset::from_hms(hour, m.try_into().unwrap(), 0).unwrap()
            },
        ),
    ))(inp)
}

pub fn parse_datetime(inp: &str) -> IResult<&str, OffsetDateTime> {
    let parser = tuple((
        parse_date,
        tag_no_case("T"),
        parse_time,
        opt(parse_tzoffset),
    ));

    map(parser, |(d, _, t, o)| {
        d.with_time(t).assume_offset(o.unwrap_or(UtcOffset::UTC))
    })(inp)
}

pub fn parse_duration(inp: &str) -> IResult<&str, Duration> {
    let days = map(terminated(digit1, tag_no_case("D")), |s: &str| {
        Duration::days(s.parse::<i64>().unwrap())
    });
    let hours = map(terminated(digit1, tag_no_case("H")), |s: &str| {
        Duration::hours(s.parse::<i64>().unwrap())
    });
    let mins = map(terminated(digit1, tag_no_case("M")), |s: &str| {
        Duration::minutes(s.parse::<i64>().unwrap())
    });

    let _s = recognize(tuple((digit1, opt(preceded(char('.'), digit1)))));
    let secs = map(terminated(_s, tag_no_case("S")), |s: &str| {
        Duration::seconds_f64(s.parse::<f64>().unwrap())
    });

    let time_duration = map(
        tuple((tag_no_case("T"), opt(hours), opt(mins), opt(secs))),
        |(_, h, m, s)| {
            let hours = h.unwrap_or(Duration::ZERO);
            let minutes = m.unwrap_or(Duration::ZERO);
            let seconds = s.unwrap_or(Duration::ZERO);
            hours.saturating_add(minutes).saturating_add(seconds)
        },
    );

    let duration_val = map(
        tuple((
            opt(one_of("+-")),
            tag_no_case("P"),
            opt(days),
            opt(time_duration),
        )),
        |(sign, _, d, t)| {
            let days = d.unwrap_or(Duration::ZERO);
            let time = t.unwrap_or(Duration::ZERO);
            let res = days.saturating_add(time);
            match sign {
                Some('-') => -1 * res,
                _ => res,
            }
        },
    );

    delimited(
        tuple((opt(tag_no_case("duration")), char('\''))),
        duration_val,
        char('\''),
    )(inp)
}

pub fn parse_binary(inp: &str) -> IResult<&str, Vec<u8>> {
    let binval = take_while(is_base64url_char);
    let parser = delimited(tag_no_case("binary'"), binval, char('\''));

    // TODO: map base64::DecodeError onto a nom Error for clarity
    map_res(parser, |b64| {
        // We make no assumptions about how the client handles b64 padding:
        let cfg = engine::GeneralPurposeConfig::new()
            .with_decode_padding_mode(engine::DecodePaddingMode::Indifferent);
        let engine = engine::GeneralPurpose::new(&alphabet::URL_SAFE, cfg);
        engine.decode(b64)
    })(inp)
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
    let guid = map(parse_guid, Literal::GUID);
    let binary = map(parse_binary, Literal::Binary);

    let date = map(parse_date, Literal::Date);
    let time = map(parse_time, Literal::Time);
    let datetime = map(parse_datetime, Literal::DateTimeOffset);
    let duration = map(parse_duration, Literal::Duration);

    alt((
        null, duration, bool, string, datetime, date, time, guid, float, int, binary,
    ))(inp)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_util::assert_parsed_to;
    use time::Month;

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

    #[test]
    fn parse_guid() {
        let guid = "d13efbec-aa20-47f4-8756-c38852488b6e";
        assert_parsed_to(parse_literal(&guid), Literal::GUID(guid.to_string()));
        assert_parsed_to(
            parse_literal(&guid.to_ascii_uppercase()),
            Literal::GUID(guid.to_ascii_uppercase()),
        );
    }

    #[test]
    fn parse_date() {
        assert_parsed_to(
            parse_literal("2023-01-01"),
            Literal::Date(Date::from_calendar_date(2023, Month::January, 1).unwrap()),
        );
        assert_parsed_to(
            parse_literal("-0001-01-01"),
            Literal::Date(Date::from_calendar_date(-1, Month::January, 1).unwrap()),
        );
    }

    #[test]
    fn parse_time() {
        assert_parsed_to(
            parse_literal("01:02"),
            Literal::Time(Time::from_hms(1, 2, 0).unwrap()),
        );
        assert_parsed_to(
            parse_literal("01:02:03"),
            Literal::Time(Time::from_hms(1, 2, 3).unwrap()),
        );
        assert_parsed_to(
            parse_literal("01:02:03.1"),
            Literal::Time(Time::from_hms_milli(1, 2, 3, 100).unwrap()),
        );
        assert_parsed_to(
            parse_literal("01:02:03.000000001"),
            Literal::Time(Time::from_hms_nano(1, 2, 3, 1).unwrap()),
        );
        assert_parsed_to(
            parse_literal("01:02:03.000000001234"),
            Literal::Time(Time::from_hms_nano(1, 2, 3, 1).unwrap()),
        );
    }

    #[test]
    fn parse_datetime() {
        assert_parsed_to(
            parse_literal("2023-01-01T00:00"),
            Literal::DateTimeOffset(
                Date::from_calendar_date(2023, Month::January, 1)
                    .unwrap()
                    .with_time(Time::from_hms(0, 0, 0).unwrap())
                    .assume_offset(UtcOffset::UTC),
            ),
        );
        assert_parsed_to(
            parse_literal("2023-01-01T00:00:01.1"),
            Literal::DateTimeOffset(
                Date::from_calendar_date(2023, Month::January, 1)
                    .unwrap()
                    .with_time(Time::from_hms_milli(0, 0, 1, 100).unwrap())
                    .assume_offset(UtcOffset::UTC),
            ),
        );
        assert_parsed_to(
            parse_literal("2023-01-01T00:00Z"),
            Literal::DateTimeOffset(
                Date::from_calendar_date(2023, Month::January, 1)
                    .unwrap()
                    .with_time(Time::from_hms(0, 0, 0).unwrap())
                    .assume_offset(UtcOffset::UTC),
            ),
        );
        assert_parsed_to(
            parse_literal("2023-01-01T00:00+02:00"),
            Literal::DateTimeOffset(
                Date::from_calendar_date(2023, Month::January, 1)
                    .unwrap()
                    .with_time(Time::from_hms(0, 0, 0).unwrap())
                    .assume_offset(UtcOffset::from_hms(2, 0, 0).unwrap()),
            ),
        );
    }

    #[test]
    fn parse_duration() {
        assert_parsed_to(
            parse_literal("duration'P1D'"),
            Literal::Duration(Duration::days(1)),
        );
        assert_parsed_to(
            parse_literal("duration'PT1H'"),
            Literal::Duration(Duration::hours(1)),
        );
        assert_parsed_to(
            parse_literal("duration'PT1M'"),
            Literal::Duration(Duration::minutes(1)),
        );
        assert_parsed_to(
            parse_literal("duration'PT1S'"),
            Literal::Duration(Duration::seconds(1)),
        );
        assert_parsed_to(
            parse_literal("duration'PT1.2S'"),
            Literal::Duration(Duration::seconds_f64(1.2)),
        );
        assert_parsed_to(
            parse_literal("duration'P1DT2H3M4.5S'"),
            Literal::Duration(
                Duration::days(1)
                    + Duration::hours(2)
                    + Duration::minutes(3)
                    + Duration::seconds_f64(4.5),
            ),
        );
        assert_parsed_to(
            parse_literal("duration'-P1D'"),
            Literal::Duration(Duration::days(-1)),
        );
        assert_parsed_to(parse_literal("'P1D'"), Literal::Duration(Duration::days(1)));
        assert_parsed_to(
            parse_literal("'-P1D'"),
            Literal::Duration(Duration::days(-1)),
        );
    }

    #[test]
    fn parse_binary() {
        let data = b"Definitely not a virus";

        let data_padded = engine::general_purpose::URL_SAFE.encode(data);
        assert_parsed_to(
            parse_literal(&format!("binary'{data_padded}'")),
            Literal::Binary(data.to_vec()),
        );

        let data_not_padded = engine::general_purpose::URL_SAFE_NO_PAD.encode(data);
        assert_parsed_to(
            parse_literal(&format!("binary'{data_not_padded}'")),
            Literal::Binary(data.to_vec()),
        );
    }
}
