const multer = require("multer");
const path = require("path");
const { v4: uuidv4 } = require("uuid");

const uploadPath = path.join(
    __dirname,
    "../../storage/uploads"
);

const storage = multer.diskStorage({

    destination: function (req, file, cb) {
        cb(null, uploadPath);
    },

    filename: function (req, file, cb) {

        const extension = path.extname(file.originalname);

        cb(
            null,
            `${uuidv4()}${extension}`
        );
    }
});


const fileFilter = (req, file, cb) => {

    const allowedTypes = [
        "application/pdf",

        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",

        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",

        "image/jpeg",
        "image/png",
        "image/webp"
    ];


    if (allowedTypes.includes(file.mimetype)) {

        cb(null, true);

    } else {

        cb(
            new Error(
                "Unsupported file type"
            ),
            false
        );
    }
};


const upload = multer({

    storage,

    limits: {
        fileSize: 50 * 1024 * 1024
    },

    fileFilter

});


module.exports = upload;
