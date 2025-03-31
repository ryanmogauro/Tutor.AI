//simple Go API with Gin
package main

import(
	"net/http"
	"errors"
	"github.com/gin-gonic/gin"
)

//Capital field names for outside access (?)
type book struct{
	ID 		string	`json:"id"`
	Title 	string	`json:"title"`
	Author	string	`json:"author"`
	Quantity int	`json:"quantity"`
}

var books = []book{
	{ID: "1", Title: "Shoe Dog", Author: "Phil Knight", Quantity: 2}, 
	{ID: "2", Title: "Zero to One", Author: "Peter Thiel", Quantity: 1}, 
	{ID: "3", Title: "Crime and Punishment", Author: "Fyodor D", Quantity: 2}, 
}

func getBooks(c *gin.Context){
	//status, data
	//auto formats json body
	c.IndentedJSON(http.StatusOK, books)
}

func createBook(c *gin.Context){
	var newBook book

	if err := c.BindJSON(&newBook); err != nil{
		return
	}
	books = append(books, newBook)
	c.IndentedJSON(http.StatusOK, newBook)
}

func bookByID(c *gin.Context){
	id := c.Param("id")
	book, err := getBookByID(id)

	if err != nil{
		c.IndentedJSON(http.StatusNotFound, gin.H{"message":"Book Not Found"})
		return
	}

	c.IndentedJSON(http.StatusOK, book)
}

//takes in target id string
//returns pointer to book if it exists
func getBookByID(id string) (*book, error){

	for i, b := range books{
		if b.ID == id{
			//returns pointer for modification by other methods
			return &books[i], nil
		}
	}
	return nil, errors.New("Book Not Found")

}

//main func
func main(){
	router := gin.Default()
	router.GET("/books", getBooks)
	router.Run("localhost:8080")
}




