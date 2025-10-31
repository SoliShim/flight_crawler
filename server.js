const express = require('express');
const app = express();

app.listen(8080, function(){
    console.log("listening on 8080")
}); //서버 열기! listen(포트번호, 실행할 코드)