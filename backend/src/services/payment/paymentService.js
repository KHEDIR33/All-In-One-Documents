const Payment = require("../../models/Payment");


async function createPayment(data){

    const payment = await Payment.create({

        phone:data.phone,

        amount:3,

        service:data.service,

        status:"pending"

    });


    return payment;

}



async function confirmPayment(id, transactionId){


    const payment =
    await Payment.findByIdAndUpdate(

        id,

        {

            status:"paid",

            transactionId:transactionId

        },

        {
            new:true
        }

    );


    return payment;

}



async function checkPayment(id){


    const payment =
    await Payment.findById(id);


    if(!payment){

        return false;

    }


    return payment.status === "paid";


}



module.exports={

    createPayment,

    confirmPayment,

    checkPayment

};
