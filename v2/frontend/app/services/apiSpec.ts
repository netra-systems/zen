
import { openApi } from "openapi-zod-client";
import { z } from "zod";

const document = openApi.document({
  openapi: "3.0.0",
  info: {
    title: "My API",
    version: "1.0.0",
  },
  paths: {},
});

class ApiSpecService {
  private spec: any = null;

  async getSpec() {
    if (this.spec) {
      return this.spec;
    }

    const response = await fetch("/openapi.json");
    this.spec = await response.json();
    return this.spec;
  }
}

export const apiSpecService = new ApiSpecService();
