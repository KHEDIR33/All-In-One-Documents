const paymentService =
require("../services/payment/paymentService");



exports.createPayment = async (req, res) => {

    try {


        const {
            phone,
            service,
            gateway
        } = req.body;



        if(!phone || !service){

            return res.status(400).json({

                success:false,

                message:"Phone and service are required"

            });

        }



        const payment =
        await paymentService.createPayment({

            phone,

            service,

            gateway: gateway || "chapa"

        });



        res.json({

            success:true,

            message:"Payment created",

            paymentId:payment._id,

            amount:payment.amount

        });



    } catch(error){


        res.status(500).json({

            success:false,

            message:"Payment creation failed",

            error:error.message

        });


    }

};
