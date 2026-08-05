const { exec } = require("child_process");


function compressPdf(inputFile, outputFile){


    return new Promise((resolve,reject)=>{


        const command =
        `gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/ebook -o "${outputFile}" "${inputFile}"`;


        exec(command,(error)=>{


            if(error){

                return reject(error);

            }


            resolve(true);


        });


    });


}


module.exports = compressPdf;
