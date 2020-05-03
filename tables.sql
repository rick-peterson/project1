CREATE TABLE users(
    id SERIAL PRIMARY KEY,
    username VARCHAR UNIQUE NOT NULL,
    password VARCHAR NOT NULL
);


CREATE TABLE books(
    id SERIAL PRIMARY KEY,
    isbn VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    author VARCHAR NOT NULL,
    year VARCHAR NOT NULL
);



CREATE TABLE reviews(
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    date_posted DATE NOT NULL DEFAULT CURRENT_TIMESTAMP, 
    user_id INTEGER REFERENCES users ,
    books_id INTEGER REFERENCES books
);



ALTER TABLE reviews ALTER COLUMN content DROP NOT NULL;

ALTER TABLE reviews ADD rating INTEGER CHECK (rating > 0 AND rating > 5);

ALTER TABLE reviews DROP CONSTRAINT reviews_rating_check;
