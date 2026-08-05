const express = require("express");

const router = express.Router();

const conversionController = require("../controllers/conversionController");

router.post(
    "/pdf-to-word",
    conversionController.pdfToWord
);

router.post(
    "/pdf-to-excel",
    conversionController.pdfToExcel
);

router.post(
    "/pdf-edit-sign",
    conversionController.pdfEditAndSign
);

router.get(
    "/download/:filename",
    conversionController.downloadFile
);

module.exports = router;
