import { Request, Response } from "express";

export const handleCustomerDataRequest = async (req: Request, res: Response) => {
  const payload = req.body;

  console.log("GDPR data request:", payload);

  // TODO: fetch customer data from DB
  return res.status(200).send("OK");
};

export const handleCustomerRedact = async (req: Request, res: Response) => {
  const payload = req.body;

  console.log("GDPR redact:", payload);

  // TODO: delete/anonymize customer data
  return res.status(200).send("OK");
};

export const handleShopRedact = async (req: Request, res: Response) => {
  const payload = req.body;

  console.log("Shop redact:", payload);

  // TODO: delete all shop data
  return res.status(200).send("OK");
};
