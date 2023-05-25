use chumsky::Parser;
use pyo3::prelude::*;

mod ast;
mod chumsky_ext;
mod parser;

/// Formats the sum of two numbers as string.
#[pyfunction]
fn parse_odata(odata_query: &str) -> PyResult<bool> {
    let res = parser::parser().parse(odata_query);
    println!("{:?}", res);
    Ok(true)
}

/// A Python module implemented in Rust.
#[pymodule]
fn _odata_query(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse_odata, m)?)?;
    Ok(())
}
