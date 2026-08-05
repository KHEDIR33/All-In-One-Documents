const express = require("express");

const router = express.Router();

const upload = require("../config/multer");

const validateFile = require("../middleware/uploadValidation");

const { uploadFile } = require("../controllers/uploadController");

router.post(
    "/",
    upload.single("file"),
    validateFile,
    uploadFile
);

module.exports = router;
