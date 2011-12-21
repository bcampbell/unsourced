
ALTER TABLE action ADD COLUMN article INTEGER REFERENCES article(id);
ALTER TABLE action ADD COLUMN source INTEGER REFERENCES source(id);
ALTER TABLE action ADD COLUMN lookup INTEGER REFERENCES lookup(id);

UPDATE action a, article_action aa SET a.article=aa.article_id WHERE a.id=aa.action_id;
UPDATE action a, source_action sa SET a.source=sa.source_id WHERE a.id=sa.action_id;
UPDATE action a, lookup_action la SET a.lookup=la.lookup_id WHERE a.id=la.action_id;


DROP TABLE article_action;
DROP TABLE source_action;
DROP TABLE lookup_action;

