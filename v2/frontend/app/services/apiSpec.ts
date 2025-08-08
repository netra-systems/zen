



class ApiSpecService {
  private spec: unknown = null;

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
