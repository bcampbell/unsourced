DROP TABLE IF EXISTS twitter_access_token;
CREATE TABLE twitter_access_token (
    user_id INT REFERENCES useraccount(id),
    token TEXT NOT NULL
);

