const express = require("express");
const cors = require("cors");
const helmet = require("helmet");
const morgan = require("morgan");
const rateLimit = require("express-rate-limit");

const connectDatabase = require("./config/database");


const app = express();


connectDatabase();


app.use(
    cors({
        origin: "*"
    })
);


app.use(helmet());

app.use(express.json());

app.use(morgan("combined"));



const limiter = rateLimit({

    windowMs: 15 * 60 * 1000,

    max: 100,

    message:{
        success:false,
        message:"Too many requests"
    }

});


app.use(limiter);



app.get("/", (req,res)=>{

    res.json({

        success:true,

        service:
        "All-In-One Documents",

        status:
        "Online"

    });

});



module.exports = app;
