BEGIN;
ALTER TABLE useraccount ADD COLUMN username VARCHAR(64) NOT NULL AFTER email;
UPDATE useraccount SET username=id;
ALTER TABLE useraccount CHANGE username username VARCHAR(64) UNIQUE NOT NULL;
ALTER TABLE useraccount CHANGE name prettyname VARCHAR(1024) NOT NULL;
ALTER TABLE useraccount ADD COLUMN auth_supplier VARCHAR(16) NOT NULL;
ALTER TABLE useraccount ADD COLUMN auth_uid VARCHAR(1024) NOT NULL;



COMMIT;


