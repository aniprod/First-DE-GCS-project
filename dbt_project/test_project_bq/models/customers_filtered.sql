{{ config(materialized='view') }}

select
    CustomerID,
    Gender,
    Age,
    `Annual_Income_USD`,
    `Spending_Score_1_100`,
    Profession,
    `Work_Experience`,
    `Family_Size`
from
    `de-1st-project`.`CTEST1`.`CT`
where
    Age >= 25
    and Profession in ('Doctor', 'Engineer')