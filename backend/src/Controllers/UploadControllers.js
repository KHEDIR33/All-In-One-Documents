const uploadFile = async (req, res) => {
    try {

        if (!req.file) {
            return res.status(400).json({
                success: false,
                message: "No file uploaded"
            });
        }


        const fileData = {
            originalName: req.file.originalname,
            fileName: req.file.filename,
            path: req.file.path,
            size: req.file.size,
            mimetype: req.file.mimetype
        };


        res.status(200).json({
            success: true,
            message: "File uploaded successfully",
            file: fileData
        });


    } catch (error) {

        console.error(error);

        res.status(500).json({
            success: false,
            message: "Upload failed",
            error: error.message
        });

    }
};


module.exports = {
    uploadFile
};
