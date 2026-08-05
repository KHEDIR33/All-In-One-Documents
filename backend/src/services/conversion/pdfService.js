const { exec } = require("child_process");
const path = require("path");


function convertPdfToWord(inputFile, outputFolder) {

    return new Promise((resolve, reject) => {


        const output =
        path.join(outputFolder);


        const command =
        `libreoffice --headless --convert-to docx "${inputFile}" --outdir "${output}"`;


        exec(command, (error) => {


            if(error){

                return reject(error);

            }


            resolve(true);


        });


    });

}



function convertWordToPdf(inputFile, outputFolder){


    return new Promise((resolve,reject)=>{


        const command =
        `libreoffice --headless --convert-to pdf "${inputFile}" --outdir "${outputFolder}"`;


        exec(command,(error)=>{


            if(error){

                return reject(error);

            }


            resolve(true);


        });


    });


}



module.exports = {

    convertPdfToWord,

    convertWordToPdf

};
