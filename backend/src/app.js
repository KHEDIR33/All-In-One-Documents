const express = require("express");
const cors = require("cors");
const helmet = require("helmet");
const morgan = require("morgan");
const rateLimit = require("express-rate-limit");

const connectDatabase = require("./config/database");

const fileRoutes = require("./routes/fileRoutes");
const paymentRoutes = require("./routes/paymentRoutes");
const uploadRoutes = require("./routes/uploadRoutes");

const errorHandler = require("./middleware/errorHandler");


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

    message: {

        success: false,

        message: "Too many requests"

    }

});


app.use(limiter);



app.use(
    "/api/files",
    fileRoutes
);


app.use(
    "/api/upload",
    uploadRoutes
);


app.use(
    "/api/payment",
    paymentRoutes
);



app.get("/", (req,res)=>{

    res.json({

        success:true,

        service:
        "All-In-One Documents",

        status:
        "Online"

    });

});


// Error handler must be last
app.use(errorHandler);



module.exports = app;
