CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    manager_id INTEGER REFERENCES employees(id)
);

CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL
);

CREATE TABLE project_members (
    project_id INTEGER NOT NULL REFERENCES projects(id),
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    PRIMARY KEY (project_id, employee_id)
);

CREATE TABLE departments (
    id INTEGER PRIMARY KEY,
    name TEXT
);
