{{ config(materialized='view') }}

select
    CustomerID,
    Gender,
    Age,
    `Annual Income USD`,
    `Spending Score 1 to 100`,
    Profession,
    `Work Experience`,
    `Family Size`
from
    `de-1st-project`.`CTEST1`.`CT`
where
    Age >= 25
    and Profession in ('Doctor', 'Engineer')