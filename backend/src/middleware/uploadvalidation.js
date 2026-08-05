const allowedTypes = [

    "application/pdf",

    "application/msword",

    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",

    "image/jpeg",

    "image/png"

];


function validateFile(req,res,next){


    if(!req.file){

        return res.status(400).json({

            success:false,

            message:"File is required"

        });

    }


    if(!allowedTypes.includes(req.file.mimetype)){


        return res.status(400).json({

            success:false,

            message:"File type not supported"

        });


    }


    next();

}



module.exports = validateFile;
