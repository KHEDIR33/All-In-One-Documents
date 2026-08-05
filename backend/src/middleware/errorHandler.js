function errorHandler(err, req, res, next) {

    console.error(err);


    // Multer upload errors
    if (err.name === "MulterError") {

        return res.status(400).json({

            success: false,

            message: err.message

        });

    }


    // Custom errors
    res.status(err.status || 500).json({

        success: false,

        message: err.message || "Server error"

    });

}


module.exports = errorHandler;
