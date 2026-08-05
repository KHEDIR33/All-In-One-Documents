const mongoose = require("mongoose");


const paymentSchema = new mongoose.Schema({

    phone:{
        type:String
    },

    amount:{
        type:Number,
        default:3
    },

    service:{
        type:String,
        required:true
    },


    transactionId:{
        type:String
    },


    status:{
        type:String,
        default:"pending"
    },


    createdAt:{
        type:Date,
        default:Date.now
    }


});


module.exports = mongoose.model(
    "Payment",
    paymentSchema
);
