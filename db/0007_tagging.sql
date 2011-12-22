CREATE TABLE tag (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(32),
    article INT NOT NULL REFERENCES article(id)
);

ALTER TABLE action ADD COLUMN tag INTEGER REFERENCES tag(id);

