# Copyright (c) 2025-2026, Tranquil Data, Inc. All rights reserved.

import json
import requests
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Optional

root_url = "http://localhost:8080/"
schema_url = root_url + "schema/"

mcp = FastMCP("TQD Service")

class Element(BaseModel):
    """
    An element in a database schema, like a table or column, which has a name and
    an optional dataype. Each element also includes a description that explains what
    the element provides and how it is used.
    """
    name: str = Field(description="the name of the schema element")
    datatype: str = Field(description="the type of associated data, like a field being of type string or date")
    description: str = Field(description="a free-form description of this element")

class Property(BaseModel):
    """
    A generic key-value structure that defines an arbitrary number of property names and values. Typically any
    collection can have multiple properties with the same name but different values.
    """
    name: str = Field(description="the name of the property")
    value: str = Field(description="the value of the property")
    datatype: Optional[str] = Field(default="string", description="the type of the value, like a string or a date")
    description: Optional[str] = Field(default="", description="a free-form description of this property")

class Relationship(BaseModel):
    """
    A single relationship that a subject has with another entity, who may or may not be a subject. Each relationship is
    of a specific type, so a subject may have multiple relationships with a given entity, but there is only one relationship
    of any give type from a subject to a given entity. Relationships may have properties that define details of the relationship.
    """
    type: str = Field(description="the type of the relationship, like a guardian or consent")
    target: str = Field(description="the name of the entity who has the relationship with the subject, who may also be a subject")
    properties: Optional[list[Property]] = Field(default=[], description="properties of the relationship, like categories of data that can be exchanged through this relationship")

class Subject(BaseModel):
    """
    A single person, company, or other entity that is associated with data, and the properties and relationships
    of that user that affect how their data can be used. For instance a subject may represent, and a property
    representing their birthday may be used by policy to decide if certain actions on their data are valid. As
    another example a subject may represent a guardian of another subject, like a parent who has responsibility
    for their child, and therefore also has rights to access some of their child's data.
    """
    properties: Optional[list[Property]] = Field(default=[], description="arbitrary properties of the subject, like where they live or when they were born")
    relationships: Optional[list[Relationship]] = Field(default=[], description="relationships that affect how data is used and shared, like a subject's employer or a user consent")

class Variable(BaseModel):
    """
    A single variable that may be used to constrain a specific value to express a purpose
    for requesting data.
    """
    name: str = Field(description="the name of this variable")
    datatype: str = Field(description="the datatype of this variable, like a string or date")
    description: Optional[str] = Field(default="", description="either a free-form description or a single URI describing the catgeory of this variable")
    obligation: bool = Field(description="true if this variable is used to filter the values that are returned in each record")
    category: str = Field(description="""The category field is a URI, and the last component of the URI describes the category of the variable:
                          - "record" if the variable is used to constrain some value from a data record
                          - "resource" if the variable is used to constrain some value about a user associated with data
                          - "group" if the variable is used to constrain some value about global state
                          - "metadata" if the variable is used to constrain values about the client request, like the type of action
                            they want to take, the purpose for that action, or the subject that is requesting this action""")

class VariableConstraint(BaseModel):
    """
    A single constraint on a Variable to express a purpose for requesting data.
    """
    variable: Variable = Field(description="the Variable that is being constrained to a specific value")
    value: str = Field(description="a specific value that expresses the purpose of requesting data")

@mcp.tool(description="returns the names of all the tables in the schema")
def get_table_names() -> list[Element]:
    """Queries the database and returns the name of all tables"""
    response = requests.get(schema_url + "categories")
    if response.status_code == 200:
        elements: list[Element] = []
        for element in response.json():
            elements.append(Element(**element))
        return elements
    response.raise_for_status()

@mcp.tool(description="returns all of the column names for the table named table_name")
def get_column_names_from_table(
        table_name: str = Field(description="name of a table from the list returned by get_table_names()"),
) -> list[Element]:
    """Returns all of the column names for the given table"""
    response = requests.get(schema_url + "fields", params={"category": table_name})
    if response.status_code == 200:
        elements: list[Element] = []
        for element in response.json():
            elements.append(Element(**element))
        return elements
    response.raise_for_status()
    
@mcp.tool(description="returns the properties and relationships of the subject named subject_name")
def get_subject(
        subject_name: str = Field(description="name of a subject"),
) -> Subject:
    """
    Returns the details of the subject named subject_name. A subject is typically a person or company, so this
    function is used to return the properties and relationships of that subject or company. Examples of a property
    are the country where a person lives or a person's date of birth. Examples of a relationships are a person's
    child, guardian, or employer.
    """
    response = requests.get(root_url + "subjects", params={"subject": subject_name})
    if response.status_code == 200:
        subject = response.json()
        return Subject(**subject)
    response.raise_for_status()

@mcp.tool(description="returns the variables used to define the purpose of a query")
def get_variables() -> list[Variable]:
    """
    In Tranquil Data all queries are on behalf of some purpose. Examples are asking for customer
    data for the purpose of sending marketing email or asking for patient data for the purpose of
    reporting on a clinical study. No query can be made without a purpose. The details of the
    purpose are expressed by setting the value of one or more variables as constraints to a query.
    Examples include constraining a subject to a particular identity, constraining a minumum age,
    constraining a location, and/or constraining use to data valid for a specific named contract or
    consent. The get_variables() function returns all possible variables that can be constrained.

    Each Variable returned from this function represents a single variable that can be constrained in
    a call to get_record_identifiers_from_variables().

    The description field is optional, but if it is present then it may contain lists explaining
    valid values or uses for the variable.
    """
    response = requests.get(root_url + "variables")
    if response.status_code == 200:
        variables: list[Variable] = []
        for variable in response.json():
            variables.append(Variable(**variable))
        return variables
    response.raise_for_status()

@mcp.tool(description="returns record identifiers valid for the purpose expressed by constraining one or more variables returned from get_variables()")
def get_record_identifiers_from_variables(
        constraints: list[VariableConstraint] = Field(description="list of constraints describing the requested set of record identifiers"),
) -> list[str]:
    """
    This function accepts one or more VariableConstraints and returns a list of unique record identifiers. The variable
    field of each VariableConstraint must be a Variable returned by get_variables(). The value constrains the return of this
    function to include only record identifiers that are valid for the purpose expressed when the Variable has the give value.
    """
    requestBody: list[dict[str, str]] = []
    for constraint in constraints:
        requestBody.append({"name": constraint.variable.name, "obligation": constraint.variable.obligation, "category": constraint.variable.category, "value": constraint.value})
    response = requests.put(root_url + "identifiers", json=requestBody)
    if response.status_code == 200:
        identifiers : list[str] = []
        for identifier in response.json():
            identifiers.append(identifier)
        return identifiers
    response.raise_for_status()

@mcp.tool(description="""accepts an arbitrary SQL query over the tables from get_table_names() and one or more
          variable constraints using the variables from get_variables(), and returns JSON-structured output.""")
def get_records_for_purpose(
        query: str = Field(description="""A SQL query over the structure returned by get_table_names() and
                           get_column_names_from_table() that is structured to return multiple individual records or
                           one record containing some aggregate values. Both return JSON-encoded records."""),
        constraints: list[VariableConstraint] = Field(description="""A list of constraints useing variables returned from
                                                      get_variables() that ensures the record(s) used and/or returned are
                                                      all valid for the constrained purpose."""),
) -> list[str]:
    """
    This function accepts an arbitrary SQL query over the described structure, usimg only the records valid for
    the constrained purpose, and returns one or more JSON documents represnting the structure of each row that the
    SQL query returns. If the query is an aggregation of some form then a single document is returned, and no records
    that are invlaid for the purpose will have been used in that operation. Otherwise, one or more documents are
    returned and all of the documents represent records that are valid for the puporse (i.e., all of their record
    identifiers would be present in a call to get_record_identifiers_from_variables() with the same variables).
    """
    response = requests.put(root_url + "records", data=query)
    if response.status_code == 200:
        records : list[str] = []
        for record in response.json():
            records.append(json.dumps(record))
        return records
    response.raise_for_status()

if __name__ == "__main__":
    mcp.run(transport="stdio")