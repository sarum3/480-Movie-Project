# Overview | CS 480 FALL 2025
### FlickFinder
Our application will have one large data set that we will break down into smaller ones, so the user can not only see the basic information for each movie, but also have a deeper understanding about who the cast of the film is and who it was directed by. 

Creating an app where users can find and create reviews of movies. There will be two entities: the user and the movies, with a relation containing the reviews. The user will be able to utilize functionality like searching for a movie, filtering by genre, rating, and  viewing similar movies.


# Data Requirements:
### User:
We record unique IDs for each user which will be used for identification. We will also need their name, username, and email address
### Movies: 
We record unique IDs for each movie to be used for identification. We will also need movie title, genre,  rating, and cast.
### Reviews:
We record reviews, ID of reviewer, and ID of movie being reviewed


# Web Technologies:
### Frontend: 
Tailwind/Booster (styling & responsive layout), HTML (page structure)
### Backend:
SQLite (database), Docker (deployment & virtual environment), Flask (routing, request handling, server logic)


# Application Requirements: 
Users must enter their name, username, password (optional), and email address before accessing or writing reviews. Upon entering their information, the application will display some of the movies in the database to allow the user to look through. Users can select a movie from the database to write and submit their review. Users can also view existing reviews from the search. 

