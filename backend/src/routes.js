const express = require("express");

const router = express.Router();


const upload = require("../utils/upload");

const validateFile =
require("../middleware/uploadValidation");


const uploadController =
require("../controllers/uploadController");



router.post(

    "/upload",

    upload.single("file"),

    validateFile,

    uploadController.uploadFile

);



module.exports = router;
