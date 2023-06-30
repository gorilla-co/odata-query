use nom::IResult;

#[cfg(test)]
pub fn assert_parsed_to<T>(result: IResult<&str, T>, exp: T)
where
    T: std::fmt::Debug + std::cmp::PartialEq,
{
    assert!(result.is_ok(), "{:?}", result);
    match result {
        Ok((rest, node)) => {
            assert!(rest.is_empty(), "Unparsed input: {rest}");
            assert_eq!(node, exp);
        }
        _ => panic!("Shouldn't occur"),
    }
}
