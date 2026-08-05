const mongoose = require("mongoose");


const fileSchema = new mongoose.Schema({

    originalName:{
        type:String,
        required:true
    },

    fileName:{
        type:String,
        required:true
    },

    filePath:{
        type:String,
        required:true
    },

    fileType:{
        type:String,
        required:true
    },

    size:{
        type:Number,
        required:true
    },

    service:{
        type:String,
        default:null
    },

    status:{
        type:String,
        default:"uploaded"
    },

    deleteAt:{
        type:Date
    },


    createdAt:{
        type:Date,
        default:Date.now
    }


});


module.exports = mongoose.model(
    "File",
    fileSchema
);
